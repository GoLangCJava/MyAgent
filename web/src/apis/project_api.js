import api from './base.js'

export async function listProjects() {
  const { data } = await api.get('/projects/')
  return data
}

export async function createProject(name, description='') {
  const { data } = await api.post('/projects/', { name, description })
  return data
}

export async function listProjectFiles(project_id, path='') {
  const { data } = await api.get(`/projects/${project_id}/files`, { params: { path } })
  return data
}

export async function readProjectFile(project_id, path) {
  const { data } = await api.get(`/projects/${project_id}/files/content`, { params: { path } })
  return data
}

export async function listWorkspaceFiles(thread_id='default', path='') {
  const { data } = await api.get('/files/workspace/list', { params: { thread_id, path } })
  return data
}

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/files/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  return data
}
