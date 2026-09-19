import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listAgents } from '../apis/agent_api.js'

export const useAgentStore = defineStore('agent', () => {
  const agents = ref([])
  const currentAgent = ref(null)
  const loading = ref(false)

  async function fetchAgents() {
    loading.value = true
    try {
      const data = await listAgents()
      agents.value = data.agents || []
      if (!currentAgent.value && agents.value.length > 0) {
        currentAgent.value = agents.value[0]
      }
    } finally {
      loading.value = false
    }
  }

  function setCurrentAgent(agent) {
    currentAgent.value = agent
  }

  return { agents, currentAgent, loading, fetchAgents, setCurrentAgent }
})
