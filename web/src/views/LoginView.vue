<template>
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)">
    <a-card style="width:400px;box-shadow:0 8px 32px rgba(0,0,0,0.2)" title="Deep Platform 登录">
      <a-form :model="form" @finish="onLogin" layout="vertical">
        <a-form-item label="用户名" name="username" :rules="[{required:true,message:'请输入用户名'}]">
          <a-input v-model:value="form.username" placeholder="admin" size="large" />
        </a-form-item>
        <a-form-item label="密码" name="password" :rules="[{required:true,message:'请输入密码'}]">
          <a-input-password v-model:value="form.password" placeholder="admin123" size="large" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" block size="large" :loading="loading">登录</a-button>
        </a-form-item>
        <div style="text-align:center;color:#999;font-size:13px">默认账号 admin / admin123<br/>支持高并发: FIFO队列 + Lease + Redis Stream + deepagents</div>
      </a-form>
    </a-card>
  </div>
</template>
<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useUserStore } from '../stores/user.js'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const form = reactive({ username: 'admin', password: 'admin123' })

async function onLogin() {
  loading.value = true
  try {
    await userStore.login(form.username, form.password)
    message.success('登录成功')
    router.push('/chat')
  } catch (e) {
    message.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>
