import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listConversations } from '../apis/conversation_api.js'

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref([])
  const loading = ref(false)

  async function fetchConversations() {
    loading.value = true
    try {
      const data = await listConversations()
      conversations.value = data.conversations || []
    } finally {
      loading.value = false
    }
  }

  return { conversations, loading, fetchConversations }
})
