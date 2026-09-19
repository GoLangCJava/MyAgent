import { ref } from 'vue'
import { createAgentRun, cancelRun as cancelRunApi } from '../apis/agent_api.js'

export function useAgentRun() {
  const messages = ref([])
  const status = ref('idle')
  const queuePosition = ref(null)
  const currentRunId = ref(null)
  const currentRequestId = ref(null)
  const error = ref(null)

  let requestES = null
  let runES = null

  function closeAll() {
    if (requestES) { requestES.close(); requestES = null }
    if (runES) { runES.close(); runES = null }
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

    const request_id = crypto.randomUUID()
    currentRequestId.value = request_id

    let res
    try {
      res = await createAgentRun({ agent_slug, thread_id, query, model_spec, request_id })
    } catch (e) {
      status.value = 'failed'
      error.value = e?.response?.data?.detail || e.message
      return
    }

    if (res.status === 'dispatched' && res.run_id) {
      startRunStream(res.run_id)
    } else {
      startRequestStream(res.request_id || request_id)
    }
  }

  function startRequestStream(request_id) {
    status.value = 'queued'
    const url = `/api/agent/requests/${request_id}/events`
    requestES = new EventSource(url)

    requestES.addEventListener('queued', (e) => {
      try {
        const data = JSON.parse(e.data)
        queuePosition.value = data.position
      } catch {}
    })

    requestES.addEventListener('run_created', (e) => {
      try {
        const data = JSON.parse(e.data)
        requestES.close()
        requestES = null
        startRunStream(data.run_id)
      } catch {}
    })

    requestES.addEventListener('cancelled', () => {
      status.value = 'cancelled'
      requestES?.close()
    })

    requestES.onerror = () => {
      // EventSource auto reconnect
    }
  }

  function startRunStream(run_id) {
    if (requestES) { requestES.close(); requestES = null }
    currentRunId.value = run_id
    status.value = 'running'
    queuePosition.value = null

    const assistantMsg = { role: 'assistant', content: '', run_id }
    messages.value.push(assistantMsg)
    const idx = messages.value.length - 1

    const url = `/api/agent/runs/${run_id}/events`
    runES = new EventSource(url)
    let lastSeq = '0-0'

    runES.addEventListener('message_delta', (e) => {
      try {
        const payload = JSON.parse(e.data)
        // payload is envelope {payload: {delta}}
        const inner = payload.payload || payload
        const delta = inner.delta || inner?.payload?.delta || ''
        if (delta) {
          messages.value[idx].content += delta
        }
        lastSeq = e.lastEventId || lastSeq
      } catch {}
    })

    runES.addEventListener('step_update', (e) => {
      // 可选: 展示工具调用
      try {
        const payload = JSON.parse(e.data)
        // console.log('step', payload)
      } catch {}
    })

    runES.addEventListener('run_completed', () => {
      status.value = 'completed'
      runES?.close()
      runES = null
    })

    runES.addEventListener('run_failed', (e) => {
      status.value = 'failed'
      try { error.value = JSON.parse(e.data).payload?.error || 'failed' } catch { error.value = 'failed' }
      runES?.close()
      runES = null
    })

    runES.addEventListener('run_cancelled', () => {
      status.value = 'cancelled'
      runES?.close()
      runES = null
    })

    runES.onerror = () => {
      // 可实现带 Last-Event-ID 重连
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
