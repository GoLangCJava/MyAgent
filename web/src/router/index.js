import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../components/Layout/MainLayout.vue'),
    children: [
      { path: '', redirect: '/chat' },
      { path: 'chat', name: 'Chat', component: () => import('../views/AgentView.vue'), meta: { title: '对话' } },
      { path: 'chat/:threadId', name: 'ChatThread', component: () => import('../views/AgentView.vue'), props: true },
      { path: 'agents', name: 'Agents', component: () => import('../views/AgentListView.vue'), meta: { title: '智能体' } },
      { path: 'conversations', name: 'Conversations', component: () => import('../views/ConversationListView.vue'), meta: { title: '会话' } },
      { path: 'projects', name: 'Projects', component: () => import('../views/ProjectView.vue'), meta: { title: '项目文件' } },
      { path: 'models', name: 'Models', component: () => import('../views/SettingsView.vue'), meta: { title: '模型设置', admin: true } },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    return next('/login')
  }
  if (to.path === '/login' && token) {
    return next('/chat')
  }
  next()
})

export default router
