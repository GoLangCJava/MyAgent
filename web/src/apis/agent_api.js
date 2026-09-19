import api from './base.js'

export async function listAgents() {
  const { data } = await api.get('/agent/')
  return data
}

export async function getAgent(slug) {
  const { data } = await api.get(`/agent/${slug}`)
  return data
}

export async function createAgent(payload) {
  const { data } = await api.post('/agent/', payload)
  return data
}

export async function updateAgent(slug, payload) {
  const { data } = await api.put(`/agent/${slug}`, payload)
  return data
}

export async function deleteAgent(slug) {
  const { data } = await api.delete(`/agent/${slug}`)
  return data
}

export async function createAgentRun({ agent_slug, thread_id, query, model_spec, queue_policy='enqueue', request_id }) {
  const { data } = await api.post('/agent/runs', { agent_slug, thread_id, query, model_spec, queue_policy, request_id })
  return data
}

export async function getRequest(request_id) {
  const { data } = await api.get(`/agent/requests/${request_id}`)
  return data
}

export async function getRun(run_id) {
  const { data } = await api.get(`/agent/runs/${run_id}`)
  return data
}

export async function cancelRun(run_id) {
  const { data } = await api.post(`/agent/runs/${run_id}/cancel`)
  return data
}

export function getRunStreamUrl(run_id, after_seq='0-0') {
  return `/api/agent/runs/${run_id}/events?after_seq=${after_seq}`
}

export function getRequestStreamUrl(request_id) {
  return `/api/agent/requests/${request_id}/events`
}
