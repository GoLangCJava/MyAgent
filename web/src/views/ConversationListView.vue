<template>
  <div style="padding:24px;max-width:800px;margin:0 auto">
    <h2>💬 历史会话</h2>
    <a-list :loading="convStore.loading" :data-source="convStore.conversations" style="background:#fff;border-radius:8px">
      <template #renderItem="{ item }">
        <a-list-item>
          <a-list-item-meta :title="item.title" :description="`${item.agent_slug} | ${new Date(item.updated_at).toLocaleString()} | ${item.thread_id.slice(0,8)}`" />
          <template #actions>
            <a @click="openChat(item.thread_id)">打开</a>
            <a-popconfirm title="确定删除?" @confirm="onDelete(item.thread_id)"><a style="color:red">删除</a></a-popconfirm>
          </template>
        </a-list-item>
      </template>
    </a-list>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useConversationStore } from '../stores/conversation.js'
import { deleteConversation } from '../apis/conversation_api.js'

const convStore = useConversationStore()
const router = useRouter()

onMounted(() => convStore.fetchConversations())

function openChat(threadId){ router.push(`/chat/${threadId}`) }
async function onDelete(threadId){
  try {
    await deleteConversation(threadId)
    message.success('已删除')
    await convStore.fetchConversations()
  } catch (e) {
    message.error('删除失败')
  }
}
</script>
