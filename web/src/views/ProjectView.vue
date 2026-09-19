<template>
  <div style="padding:24px;max-width:1000px;margin:0 auto">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
      <h2>📁 项目文件</h2>
      <a-button type="primary" @click="showCreate=true">创建项目</a-button>
    </div>

    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="项目列表" size="small">
          <a-list :data-source="projects" :loading="loading">
            <template #renderItem="{ item }">
              <a-list-item :class="{active: selectedProject?.id===item.id}" @click="selectProject(item)" style="cursor:pointer">
                <a-list-item-meta :title="item.name" :description="item.workdir_path" />
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-card :title="selectedProject ? `${selectedProject.name} - ${currentPath || '/'}` : '请选择项目'" size="small" :extra="selectedProject ? `Workdir: ${selectedProject.workdir_path}` : ''">
          <a-breadcrumb style="margin-bottom:12px">
            <a-breadcrumb-item @click="navigateTo('')" style="cursor:pointer">根目录</a-breadcrumb-item>
            <a-breadcrumb-item v-for="(p,i) in pathParts" :key="i" @click="navigateTo(pathParts.slice(0,i+1).join('/'))" style="cursor:pointer">{{ p }}</a-breadcrumb-item>
          </a-breadcrumb>
          <a-list :data-source="files" :loading="fileLoading">
            <template #renderItem="{ item }">
              <a-list-item @click="onFileClick(item)" style="cursor:pointer">
                <span>{{ item.is_dir ? '📁' : '📄' }} {{ item.name }}</span>
                <span style="color:#999">{{ item.is_dir ? '' : formatSize(item.size) }}</span>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <a-modal v-model:open="showCreate" title="创建项目" @ok="onCreate">
      <a-input v-model:value="newProjectName" placeholder="项目名称" />
    </a-modal>

    <a-modal v-model:open="previewOpen" :title="previewPath" width="800px" :footer="null">
      <pre style="background:#1e1e1e;color:#d4d4d4;padding:16px;border-radius:6px;max-height:60vh;overflow:auto">{{ previewContent }}</pre>
    </a-modal>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { listProjects, createProject, listProjectFiles, readProjectFile } from '../apis/project_api.js'

const projects = ref([])
const loading = ref(false)
const selectedProject = ref(null)
const files = ref([])
const fileLoading = ref(false)
const currentPath = ref('')
const showCreate = ref(false)
const newProjectName = ref('')
const previewOpen = ref(false)
const previewContent = ref('')
const previewPath = ref('')

const pathParts = computed(() => currentPath.value ? currentPath.value.split('/').filter(Boolean) : [])

function formatSize(s){ if(s<1024) return s+'B'; if(s<1024*1024) return (s/1024).toFixed(1)+'KB'; return (s/1024/1024).toFixed(1)+'MB' }

onMounted(fetchProjects)

async function fetchProjects(){
  loading.value=true
  try {
    const data = await listProjects()
    projects.value = data.projects || []
    if (projects.value.length>0) selectProject(projects.value[0])
  } finally { loading.value=false }
}

async function selectProject(proj){
  selectedProject.value = proj
  currentPath.value = ''
  await loadFiles()
}

async function loadFiles(){
  if (!selectedProject.value) return
  fileLoading.value=true
  try {
    const data = await listProjectFiles(selectedProject.value.id, currentPath.value)
    files.value = data.files || []
  } catch (e) {
    message.error('加载失败')
  } finally { fileLoading.value=false }
}

function navigateTo(path){
  currentPath.value = path
  loadFiles()
}

async function onFileClick(item){
  if (item.is_dir) {
    currentPath.value = item.path
    await loadFiles()
  } else {
    try {
      const data = await readProjectFile(selectedProject.value.id, item.path)
      previewContent.value = data.content
      previewPath.value = item.path
      previewOpen.value = true
    } catch {
      message.error('读取失败')
    }
  }
}

async function onCreate(){
  if (!newProjectName.value.trim()) return
  try {
    await createProject(newProjectName.value)
    message.success('创建成功')
    showCreate.value=false
    newProjectName.value=''
    await fetchProjects()
  } catch (e) {
    message.error('创建失败')
  }
}
</script>
<style>
.active { background:#e6f4ff; }
</style>
