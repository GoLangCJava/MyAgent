<template>
  <div class="message-item" :class="message.role">
    <div class="message-avatar" :class="message.role">
      {{ message.role==='user' ? '🧑' : '🤖' }}
    </div>
    <div class="message-content">
      <div v-if="message.role==='user'">{{ message.content }}</div>
      <div v-else class="markdown-content" v-html="rendered"></div>
      <div v-if="message.role==='assistant' && isStreaming" style="display:inline-block;width:8px;height:16px;background:#1677ff;animation:blink 1s infinite;margin-left:4px"></div>
    </div>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps({
  message: Object,
  isStreaming: Boolean
})

const md = new MarkdownIt({
  highlight: function(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try { return hljs.highlight(str, { language: lang }).value } catch {}
    }
    return ''
  }
})

const rendered = computed(() => {
  try {
    return md.render(props.message.content || '')
  } catch {
    return props.message.content
  }
})
</script>
<style>
@keyframes blink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
</style>
