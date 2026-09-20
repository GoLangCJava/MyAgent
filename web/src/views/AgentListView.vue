<template>
  <div style="padding:24px;max-width:1200px;margin:0 auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
      <h2>🤖 智能体管理</h2>
      <a-button type="primary" @click="showCreate=true">创建智能体</a-button>
    </div>
    <a-row :gutter="16">
      <a-col :span="8" v-for="agent in agentStore.agents" :key="agent.slug" style="margin-bottom:16px">
        <a-card :title="`${agent.icon} ${agent.name}`" :extra="agent.is_builtin ? '内置' : ''">
          <p style="color:#666;min-height:40px">{{ agent.description }}</p>
          <p style="font-size:12px;color:#999">Slug: {{ agent.slug }} | Backend: {{ agent.backend_id }}</p>
          <template #actions>
            <a @click="editAgent(agent)">编辑</a>
            <a v-if="!agent.is_builtin" @click="deleteAgent(agent)" style="color:red">删除</a>
            <a @click="useAgent(agent)">使用</a>
          </template>
        </a-card>
      </a-col>
    </a-row>

    <a-modal v-model:open="showCreate" title="创建/编辑智能体" @ok="onSave" :confirm-loading="saving">
      <a-form layout="vertical">
        <a-form-item label="Slug (唯一标识)"><a-input v-model:value="form.slug" :disabled="isEdit" placeholder="my-agent" /></a-form-item>
        <a-form-item label="名称"><a-input v-model:value="form.name" placeholder="我的智能体" /></a-form-item>
        <a-form-item label="图标"><a-input v-model:value="form.icon" placeholder="🤖" /></a-form-item>
        <a-form-item label="描述"><a-textarea v-model:value="form.description" :rows="2" /></a-form-item>
        <a-form-item label="System Prompt"><a-textarea v-model:value="form.system_prompt" :rows="6" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAgentStore } from '../stores/agent.js'
import { createAgent, updateAgent, deleteAgent as deleteApi } from '../apis/agent_api.js'
import { genUUID } from '../utils/uuid.js'

const agentStore = useAgentStore()
const router = useRouter()
const showCreate = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const form = reactive({ slug:'', name:'', icon:'🤖', description:'', system_prompt:'You are a helpful assistant.' })
let editingSlug = ''

onMounted(() => agentStore.fetchAgents())

function editAgent(agent){
  isEdit.value=true
  editingSlug=agent.slug
  form.slug=agent.slug
  form.name=agent.name
  form.icon=agent.icon
  form.description=agent.description
  form.system_prompt=agent.system_prompt
  showCreate.value=true
}
function useAgent(agent){
  agentStore.setCurrentAgent(agent)
  router.push(`/chat/${genUUID()}`)
}
async function onSave(){
  saving.value=true
  try {
    if (isEdit.value) {
      await updateAgent(editingSlug, { name:form.name, icon:form.icon, description:form.description, system_prompt:form.system_prompt })
      message.success('更新成功')
    } else {
      await createAgent(form)
      message.success('创建成功')
    }
    showCreate.value=false
    isEdit.value=false
    await agentStore.fetchAgents()
  } catch (e) {
    message.error(e.response?.data?.detail || '失败')
  } finally { saving.value=false }
}
async function deleteAgent(agent){
  try {
    await deleteApi(agent.slug)
    message.success('删除成功')
    await agentStore.fetchAgents()
  } catch (e) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}
</script>
