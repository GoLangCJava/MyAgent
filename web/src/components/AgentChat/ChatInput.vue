<template>
  <div style="padding:16px;border-top:1px solid #f0f0f0;background:#fff">
    <div style="display:flex;gap:8px;align-items:flex-end;max-width:900px;margin:0 auto">
      <a-select v-model:value="selectedModel" style="width:200px" placeholder="模型" :options="modelOptions" size="large" />
      <a-textarea v-model:value="input" placeholder="输入消息... Enter发送 Shift+Enter换行" :auto-size="{minRows:1,maxRows:6}" @pressEnter="onPressEnter" style="flex:1" />
      <a-button v-if="status==='running'" danger @click="$emit('cancel')" size="large">停止</a-button>
      <a-button v-else type="primary" @click="send" :disabled="!input.trim()" size="large">发送</a-button>
    </div>
    <div v-if="status==='queued'" style="text-align:center;margin-top:8px;color:#faad14">排队中... 位置 {{ queuePosition }}</div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { listModelSpecs } from '../../apis/model_api.js'

const props = defineProps({ status: String, queuePosition: Number })
const emit = defineEmits(['send','cancel'])
const input = ref('')
const selectedModel = ref('openai:gpt-4o-mini')
const modelOptions = ref([{label:'openai:gpt-4o-mini', value:'openai:gpt-4o-mini'}])

onMounted(async () => {
  try {
    const data = await listModelSpecs()
    modelOptions.value = data.specs.map(s => ({label:s, value:s}))
    if (modelOptions.value.length>0) selectedModel.value = modelOptions.value[0].value
  } catch {}
})

function onPressEnter(e) {
  if (!e.shiftKey) {
    e.preventDefault()
    send()
  }
}
function send() {
  if (!input.value.trim()) return
  emit('send', { query: input.value, model_spec: selectedModel.value })
  input.value = ''
}
</script>
