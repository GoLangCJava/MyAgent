import api from './base.js'

export async function login(username, password) {
  const { data } = await api.post('/auth/login', { username, password })
  return data
}

export async function register(username, password, email='') {
  const { data } = await api.post('/auth/register', { username, password, email })
  return data
}

export async function getMe() {
  const { data } = await api.get('/auth/me')
  return data
}

export async function listUsers() {
  const { data } = await api.get('/auth/users')
  return data
}
