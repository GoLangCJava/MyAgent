import { ref } from 'vue'
import { createAgentRun, cancelRun as cancelRunApi } from '../apis/agent_api.js'
import { genUUID } from '../utils/uuid.js'

function authHeaders() {
  const token = localStorage.getItem('token') || ''
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function handleUnauthorized(res) {
  // 与 axios 拦截器保持一致: 401 则清 token 并回登录页
  if (res.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    if (location.pathname !== '/login') {
      location.href = '/login'
    }
    return true
  }
  return false
}

// SSE 帧解析 (参考 Yuxi 的 processRunSseResponse)
async function readSseStream(response, onEvent) {
  if (!response || !response.body) return
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventType = 'message'
  let eventId = null
  let dataLines = []

  const dispatch = () => {
    if (dataLines.length === 0) return
    const dataText = dataLines.join('\n')
    try {
      onEvent(eventType, JSON.parse(dataText), eventId)
    } catch {}
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const rawLine of lines) {
        const line = rawLine.replace(/\r$/, '')
        if (!line) {
          dispatch()
          eventType = 'message'
          eventId = null
          dataLines = []
          continue
        }
        if (line.startsWith(':')) continue // 心跳注释
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim() || 'message'
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trimStart())
        } else if (line.startsWith('id:')) {
          eventId = line.slice(3).trim()
        }
      }
    }
    dispatch()
  } finally {
    try { reader.releaseLock() } catch {}
  }
}

export function useAgentRun() {
  const messages = ref([])
  const status = ref('idle')
  const queuePosition = ref(null)
  const currentRunId = ref(null)
  const currentRequestId = ref(null)
  const error = ref(null)

  let requestCtrl = null
  let runCtrl = null

  function closeAll() {
    if (requestCtrl) { try { requestCtrl.abort() } catch {} ; requestCtrl = null }
    if (runCtrl) { try { runCtrl.abort() } catch {} ; runCtrl = null }
  }

  function setMessagesFromHistory(historyMessages) {
    messages.value = historyMessages.map(m => ({ role: m.role, content: m.content, run_id: m.run_id }))
  }

  async function sendMessage({ agent_slug='chatbot', thread_id, query, model_spec }) {
    closeAll()
    const userMsg = { role: 'user', content: query }
    messages.value.push(userMsg)
    status.value = 'queued'
    error.value = null

    const request_id = genUUID()
    currentRequestId.value = request_id

    console.log('[chat] 发送', { agent_slug, thread_id, query_len: query.length, model_spec, request_id })
    let res
    try {
      res = await createAgentRun({ agent_slug, thread_id, query, model_spec, request_id })
      console.log('[chat] 建单响应', res)
    } catch (e) {
      status.value = 'failed'
      error.value = e?.response?.data?.detail || e.message
      console.error('[chat] 建单失败', error.value)
      return
    }

    if (res.status === 'dispatched' && res.run_id) {
      startRunStream(res.run_id)
    } else {
      startRequestStream(res.request_id || request_id)
    }
  }

  async function startRequestStream(request_id) {
    closeAll()
    status.value = 'queued'
    const ctrl = new AbortController()
    requestCtrl = ctrl

    let res
    try {
      res = await fetch(`/api/agent/requests/${request_id}/events`, {
        headers: authHeaders(),
        signal: ctrl.signal
      })
    } catch (e) {
      if (e.name === 'AbortError') return
      status.value = 'failed'
      error.value = 'SSE 连接失败'
      return
    }
    if (!res.ok) {
      if (!handleUnauthorized(res)) {
        status.value = 'failed'
        error.value = `SSE 连接失败: ${res.status}`
      }
      return
    }

    try {
      await readSseStream(res, (type, data) => {
        if (type === 'queued') {
          queuePosition.value = data.position
        } else if (type === 'run_created') {
          console.log('[chat] run 已创建, 切 run 流:', data.run_id)
          if (requestCtrl === ctrl) { try { ctrl.abort() } catch {} ; requestCtrl = null }
          startRunStream(data.run_id)
        } else if (type === 'cancelled' || type === 'rejected' || type === 'failed') {
          console.log('[chat] request 终态:', type)
          status.value = type === 'cancelled' ? 'cancelled' : 'failed'
        } else if (type === 'error') {
          console.error('[chat] request 流错误:', data.message)
          status.value = 'failed'
          error.value = data.message || 'failed'
        }
      })
    } catch (e) {
      if (e.name !== 'AbortError') {
        status.value = 'failed'
        error.value = 'SSE 读取中断'
      }
    }
  }

  async function startRunStream(run_id) {
    if (requestCtrl) { try { requestCtrl.abort() } catch {} ; requestCtrl = null }
    if (runCtrl) { try { runCtrl.abort() } catch {} ; runCtrl = null }
    currentRunId.value = run_id
    status.value = 'running'
    queuePosition.value = null

    const assistantMsg = { role: 'assistant', content: '', run_id }
    messages.value.push(assistantMsg)
    const idx = messages.value.length - 1

    const ctrl = new AbortController()
    runCtrl = ctrl

    let res
    try {
      res = await fetch(`/api/agent/runs/${run_id}/events`, {
        headers: authHeaders(),
        signal: ctrl.signal
      })
    } catch (e) {
      if (e.name === 'AbortError') return
      status.value = 'failed'
      error.value = 'SSE 连接失败'
      return
    }
    if (!res.ok) {
      if (!handleUnauthorized(res)) {
        status.value = 'failed'
        error.value = `SSE 连接失败: ${res.status}`
      }
      return
    }

    let gotDelta = false
    console.log('[chat] 订阅 run 流:', run_id)
    try {
      await readSseStream(res, (type, data, eventId) => {
        const inner = data.payload || data
        if (type === 'message_delta') {
          const delta = inner.delta || inner?.payload?.delta || ''
          if (delta) {
            if (!gotDelta) { gotDelta = true; console.log('[chat] 首个 delta 到达') }
            messages.value[idx].content += delta
          }
        } else if (type === 'step_update') {
          // 可选: 展示工具调用
        } else if (type === 'run_completed') {
          console.log('[chat] run 完成, 输出长度:', messages.value[idx].content.length)
          status.value = 'completed'
        } else if (type === 'run_failed') {
          console.error('[chat] run 失败:', inner.error || inner?.payload?.error)
          status.value = 'failed'
          error.value = inner.error || inner?.payload?.error || 'failed'
        } else if (type === 'run_cancelled') {
          console.log('[chat] run 已取消')
          status.value = 'cancelled'
        }
      })
    } catch (e) {
      if (e.name !== 'AbortError') {
        status.value = 'failed'
        error.value = 'SSE 读取中断'
      }
    } finally {
      if (runCtrl === ctrl) runCtrl = null
    }
  }

  async function cancel() {
    if (!currentRunId.value) return
    try {
      await cancelRunApi(currentRunId.value)
      status.value = 'cancelled'
      closeAll()
    } catch (e) {
      error.value = e.message
    }
  }

  return { messages, status, queuePosition, currentRunId, currentRequestId, error, sendMessage, cancel, closeAll, setMessagesFromHistory }
}
