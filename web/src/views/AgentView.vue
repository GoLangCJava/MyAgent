<template>
  <div style="display:flex;height:100vh;overflow:hidden">
    <!-- 中间对话区 -->
    <div style="flex:1;display:flex;flex-direction:column;background:#fff">
      <div style="height:64px;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;padding:0 20px;justify-content:space-between">
        <div style="display:flex;align-items:center;gap:12px">
          <a-avatar :style="{background:'#1677ff'}">{{ currentAgent?.icon || '🤖' }}</a-avatar>
          <div>
            <div style="font-weight:600">{{ currentAgent?.name || '选择智能体' }}</div>
            <div style="font-size:12px;color:#999">{{ currentAgent?.description }}</div>
          </div>
          <a-select v-model:value="selectedAgentSlug" :options="agentOptions" style="width:160px;margin-left:16px" @change="onAgentChange" placeholder="切换智能体" />
        </div>
        <div style="display:flex;gap:8px">
          <a-button @click="clearChat">清空</a-button>
          <a-button @click="showWorkspace=!showWorkspace">{{ showWorkspace?'隐藏文件':'文件' }}</a-button>
        </div>
      </div>

      <div ref="messageListRef" class="message-list" style="flex:1;overflow-y:auto;padding:20px;background:#fafafa">
        <div v-if="messages.length===0" style="text-align:center;padding:60px 20px;color:#999">
          <div style="font-size:48px;margin-bottom:16px">🤖</div>
          <h3>Deep Platform - 基于 deepagents</h3>
          <p>支持规划(todo)、子智能体(task)、文件系统、上下文压缩</p>
          <p>高并发: 线程级FIFO + Lease租约 + Redis Stream</p>
          <div style="margin-top:20px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap">
            <a-tag v-for="q in quickQuestions" :key="q" @click="sendQuick(q)" style="cursor:pointer">{{ q }}</a-tag>
          </div>
        </div>
        <ChatMessage v-for="(m,i) in messages" :key="i" :message="m" :is-streaming="status==='running' && i===messages.length-1 && m.role==='assistant'" />
        <div v-if="status==='running'" style="padding:8px 0;color:#999;font-size:13px"><a-spin size="small" /> 思考中... {{ currentRunId?.slice(0,8) }}</div>
      </div>

      <ChatInput :status="status" :queue-position="queuePosition" @send="onSend" @cancel="cancel" />
    </div>

    <!-- 右侧文件区 -->
    <div v-if="showWorkspace" style="width:320px;border-left:1px solid #f0f0f0;background:#fff;display:flex;flex-direction:column">
      <div style="height:64px;border-bottom:1px solid #f0f0f0;display:flex;align-items:center;padding:0 16px;font-weight:600">📁 Workspace</div>
      <div style="flex:1;overflow-y:auto;padding:12px">
        <div v-if="workspaceFiles.length===0" style="color:#999;text-align:center;padding:20px">暂无文件<br/>智能体会自动写入 /workspace</div>
        <div v-for="f in workspaceFiles" :key="f.path" style="padding:6px 8px;border-radius:4px;cursor:pointer;display:flex;justify-content:space-between" @click="previewFile(f)">
          <span><span v-if="f.is_dir">📁</span><span v-else>📄</span> {{ f.name }}</span>
          <span v-if="!f.is_dir" style="color:#999;font-size:12px">{{ formatSize(f.size) }}</span>
        </div>
      </div>
      <div style="padding:8px;border-top:1px solid #f0f0f0">
        <a-button size="small" block @click="loadWorkspace">刷新</a-button>
      </div>
    </div>

    <a-modal v-model:open="previewOpen" :title="previewPath" width="800px" :footer="null">
      <pre style="background:#1e1e1e;color:#d4d4d4;padding:16px;border-radius:6px;max-height:60vh;overflow:auto;white-space:pre-wrap">{{ previewContent }}</pre>
    </a-modal>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAgentStore } from '../stores/agent.js'
import { getConversation } from '../apis/conversation_api.js'
import { listWorkspaceFiles } from '../apis/project_api.js'
import ChatMessage from '../components/AgentChat/ChatMessage.vue'
import ChatInput from '../components/AgentChat/ChatInput.vue'
import { useAgentRun } from '../composables/useAgentRun.js'
import { genUUID } from '../utils/uuid.js'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()
const { messages, status, queuePosition, currentRunId, error, sendMessage, cancel, closeAll, setMessagesFromHistory } = useAgentRun()

const threadId = ref(route.params.threadId || localStorage.getItem('thread_id') || genUUID())
const selectedAgentSlug = ref('chatbot')
const showWorkspace = ref(true)
const workspaceFiles = ref([])
const previewOpen = ref(false)
const previewContent = ref('')
const previewPath = ref('')
const messageListRef = ref(null)

const quickQuestions = ref(['帮我写一个Python爬虫并保存到文件','研究LangGraph deepagents并生成报告','列出workspace文件并分析','写一个数据分析脚本'])

const currentAgent = computed(() => agentStore.agents.find(a => a.slug===selectedAgentSlug.value) || agentStore.currentAgent)
const agentOptions = computed(() => agentStore.agents.map(a => ({label:`${a.icon} ${a.name}`, value:a.slug})))

function formatSize(s){ if(s<1024) return s+'B'; if(s<1024*1024) return (s/1024).toFixed(1)+'KB'; return (s/1024/1024).toFixed(1)+'MB' }

watch(() => route.params.threadId, (newId) => {
  if (newId && newId!==threadId.value) {
    threadId.value = newId
    loadHistory()
  }
})

onMounted(async () => {
  await agentStore.fetchAgents()
  if (agentStore.agents.length>0) selectedAgentSlug.value = agentStore.agents[0].slug
  if (route.params.threadId) {
    threadId.value = route.params.threadId
    await loadHistory()
  } else {
    const tid = threadId.value
    router.replace(`/chat/${tid}`)
  }
  loadWorkspace()
})

async function loadHistory() {
  try {
    const data = await getConversation(threadId.value)
    setMessagesFromHistory(data.messages || [])
    scrollToBottom()
  } catch {
    messages.value = []
  }
}

function onAgentChange(v){ selectedAgentSlug.value=v }

async function onSend({ query, model_spec }) {
  localStorage.setItem('thread_id', threadId.value)
  await sendMessage({ agent_slug: selectedAgentSlug.value, thread_id: threadId.value, query, model_spec })
  await nextTick()
  scrollToBottom()
  setTimeout(loadWorkspace, 2000)
}

function scrollToBottom(){
  nextTick(() => {
    if (messageListRef.value) messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  })
}

watch(messages, () => scrollToBottom(), { deep:true })

function clearChat(){
  messages.value=[]
  closeAll()
  const tid=genUUID()
  threadId.value=tid
  router.push(`/chat/${tid}`)
}

function sendQuick(q){ onSend({ query:q, model_spec:'openai:gpt-4o-mini' }) }

async function loadWorkspace(){
  try {
    const data = await listWorkspaceFiles(threadId.value, '')
    workspaceFiles.value = data.files || []
  } catch { workspaceFiles.value=[] }
}

async function previewFile(f){
  if (f.is_dir) {
    // 可扩展进入子目录
    return
  }
  try {
    const data = await listWorkspaceFiles(threadId.value, f.path)
    // 简化: 直接用接口读文件内容需另加, 这里 mock
    previewPath.value = f.path
    previewContent.value = `文件: ${f.path}\n大小: ${f.size}\n\n(实际内容需通过后端 /files/workspace/content 接口获取)\n\n提示: 智能体已写入 ${f.name}`
    previewOpen.value = true
  } catch (e) {
    previewContent.value = '加载失败 '+e.message
    previewOpen.value = true
  }
}
</script>
