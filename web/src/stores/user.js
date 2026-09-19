import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, getMe } from '../apis/auth.js'

export const useUserStore = defineStore('user', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('token') || '')

  async function login(username, password) {
    const data = await loginApi(username, password)
    token.value = data.access_token
    user.value = data.user
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify(data.user))
    return data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function fetchMe() {
    const data = await getMe()
    user.value = data
    localStorage.setItem('user', JSON.stringify(data))
    return data
  }

  return { user, token, login, logout, fetchMe }
})
