import api from './base.js'

export async function listConversations() {
  const { data } = await api.get('/conversations/')
  return data
}

export async function getConversation(thread_id) {
  const { data } = await api.get(`/conversations/${thread_id}`)
  return data
}

export async function updateConversation(thread_id, payload) {
  const { data } = await api.put(`/conversations/${thread_id}`, payload)
  return data
}

export async function deleteConversation(thread_id) {
  const { data } = await api.delete(`/conversations/${thread_id}`)
  return data
}
