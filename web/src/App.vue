<template>
  <a-config-provider :theme="{ token: { colorPrimary: '#1677ff' } }">
    <router-view />
  </a-config-provider>
</template>
<script setup>
import { onMounted } from 'vue'
import { useUserStore } from './stores/user.js'
const userStore = useUserStore()
onMounted(async () => {
  if (localStorage.getItem('token')) {
    try { await userStore.fetchMe() } catch {}
  }
})
</script>
