<template>
  <div style="padding:24px;max-width:800px;margin:0 auto">
    <h2>⚙️ 模型设置</h2>
    <a-card title="系统状态" style="margin-bottom:16px">
      <a-descriptions :column="2" bordered size="small">
        <a-descriptions-item label="Postgres">{{ readyInfo.postgres || 'checking' }}</a-descriptions-item>
        <a-descriptions-item label="Redis">{{ readyInfo.redis || 'checking' }}</a-descriptions-item>
        <a-descriptions-item label="Runs">{{ stats.runs }}</a-descriptions-item>
        <a-descriptions-item label="Conversations">{{ stats.conversations }}</a-descriptions-item>
        <a-descriptions-item label="Users">{{ stats.users }}</a-descriptions-item>
        <a-descriptions-item label="Agents">{{ stats.agents }}</a-descriptions-item>
      </a-descriptions>
    </a-card>

    <a-card title="模型提供商" :extra="`${providers.length} 个`">
      <a-list :data-source="providers" :loading="loading">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-list-item-meta :title="`${item.provider}:${item.name}`" :description="item.base_url || 'default base'" />
            <template #actions>
              <a @click="onDelete(item.id)" style="color:red">删除</a>
            </template>
          </a-list-item>
        </template>
      </a-list>
      <div style="margin-top:16px">
        <h4>添加提供商</h4>
        <a-form layout="inline" :model="form" @finish="onAdd">
          <a-form-item><a-input v-model:value="form.name" placeholder="名称" /></a-form-item>
          <a-form-item><a-select v-model:value="form.provider" :options="[{label:'siliconflow',value:'siliconflow'},{label:'openai',value:'openai'},{label:'anthropic',value:'anthropic'}]" style="width:130px" /></a-form-item>
          <a-form-item><a-input v-model:value="form.api_key" placeholder="API Key" style="width:200px" /></a-form-item>
          <a-form-item><a-input v-model:value="form.base_url" placeholder="Base URL (选填)" style="width:220px" /></a-form-item>
          <a-form-item><a-button type="primary" html-type="submit">添加</a-button></a-form-item>
        </a-form>
      </div>
    </a-card>

    <a-card title="可用模型 Specs" style="margin-top:16px">
      <a-tag v-for="s in specs" :key="s" style="margin:4px">{{ s }}</a-tag>
    </a-card>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { listModelProviders, listModelSpecs, createModelProvider, getSystemStats, getSystemReady } from '../apis/model_api.js'
import api from '../apis/base.js'

const providers = ref([])
const specs = ref([])
const stats = ref({})
const readyInfo = ref({})
const loading = ref(false)
const form = reactive({ name:'', provider:'siliconflow', api_key:'', base_url:'https://api.siliconflow.cn/v1', models_json:{models:['Qwen/Qwen2.5-7B-Instruct']} })

onMounted(async () => {
  await fetchProviders()
  await fetchSpecs()
  try { stats.value = await getSystemStats() } catch {}
  try { readyInfo.value = await getSystemReady() } catch {}
})

async function fetchProviders(){
  loading.value=true
  try {
    const data = await listModelProviders()
    providers.value = data.providers || []
  } finally { loading.value=false }
}
async function fetchSpecs(){
  try {
    const data = await listModelSpecs()
    specs.value = data.specs || []
  } catch {}
}
async function onAdd(){
  try {
    await createModelProvider(form)
    message.success('添加成功')
    form.name=''
    await fetchProviders()
    await fetchSpecs()
  } catch (e) {
    message.error(e.response?.data?.detail || '失败')
  }
}
async function onDelete(id){
  try {
    await api.delete(`/models/${id}`)
    message.success('删除成功')
    await fetchProviders()
  } catch { message.error('删除失败') }
}
</script>
