<template>
  <a-layout style="min-height:100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible :width="260" theme="light" style="border-right:1px solid #f0f0f0">
      <div style="height:64px;display:flex;align-items:center;padding:0 20px;font-weight:bold;font-size:18px;border-bottom:1px solid #f0f0f0">
        <span v-if="!collapsed">🤖 Deep Platform</span>
        <span v-else>🤖</span>
      </div>
      <div style="padding:12px">
        <a-button type="primary" block @click="newChat" style="margin-bottom:16px">
          <template #icon><PlusOutlined /></template>
          新对话
        </a-button>
      </div>
      <a-menu v-model:selectedKeys="selectedKeys" mode="inline" @click="onMenuClick">
        <a-menu-item key="/chat"><MessageOutlined /> 对话</a-menu-item>
        <a-menu-item key="/conversations"><HistoryOutlined /> 历史会话</a-menu-item>
        <a-menu-item key="/agents"><RobotOutlined /> 智能体</a-menu-item>
        <a-menu-item key="/projects"><FolderOutlined /> 项目文件</a-menu-item>
        <a-menu-item key="/models" v-if="userStore.user?.is_admin"><SettingOutlined /> 模型设置</a-menu-item>
      </a-menu>

      <div style="position:absolute;bottom:0;width:100%;padding:12px;border-top:1px solid #f0f0f0">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
          <a-avatar :style="{background:'#1677ff'}">{{ userStore.user?.username?.[0]?.toUpperCase() }}</a-avatar>
          <div v-if="!collapsed" style="flex:1;overflow:hidden">
            <div style="font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ userStore.user?.username }}</div>
            <div style="font-size:12px;color:#999">{{ userStore.user?.is_admin ? '管理员' : '用户' }}</div>
          </div>
        </div>
        <a-button block size="small" @click="logout" v-if="!collapsed">退出</a-button>
      </div>
    </a-layout-sider>
    <a-layout>
      <a-layout-content style="background:#fff;overflow:hidden;display:flex;flex-direction:column">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>
<script setup>
import { ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../../stores/user.js'
import { PlusOutlined, MessageOutlined, HistoryOutlined, RobotOutlined, FolderOutlined, SettingOutlined } from '@ant-design/icons-vue'

const collapsed = ref(false)
const selectedKeys = ref(['/chat'])
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

watch(() => route.path, (p) => {
  if (p.startsWith('/chat')) selectedKeys.value = ['/chat']
  else selectedKeys.value = [p]
}, { immediate:true })

function onMenuClick({ key }) {
  router.push(key)
}
function newChat() {
  const tid = crypto.randomUUID()
  router.push(`/chat/${tid}`)
}
function logout() {
  userStore.logout()
  router.push('/login')
}
</script>
