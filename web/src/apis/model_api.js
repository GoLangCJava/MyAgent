import api from './base.js'

export async function listModelProviders() {
  const { data } = await api.get('/models/')
  return data
}

export async function listModelSpecs() {
  const { data } = await api.get('/models/specs')
  return data
}

export async function createModelProvider(payload) {
  const { data } = await api.post('/models/', payload)
  return data
}

export async function getSystemStats() {
  const { data } = await api.get('/system/stats')
  return data
}

export async function getSystemReady() {
  const { data } = await api.get('/system/ready')
  return data
}
