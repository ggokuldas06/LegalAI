<!-- src/components/chat/ChatMessage.vue -->
<template>
  <div class="chat-message" :class="message.role">
    <div class="message-avatar">
      <i :class="avatarIcon"></i>
    </div>
    
    <div class="message-content">
      <div class="message-header">
        <strong>{{ roleLabel }}</strong>
        <small class="text-muted">{{ formattedTime }}</small>
      </div>
      
      <div class="message-body">
        <div v-if="message.role === 'error'" class="alert alert-danger mb-0">
          {{ message.content }}
        </div>
        
        <div v-else-if="message.role === 'user'" class="user-message">
          {{ message.content }}
        </div>
        
        <div v-else class="assistant-message">
          <div class="message-text" v-html="formattedContent"></div>
          
          <!-- Citations -->
          <div v-if="message.citations && message.citations.length > 0" class="citations mt-3">
            <strong class="d-block mb-2">
              <i class="bi bi-quote me-1"></i>
              Citations ({{ message.citations.length }})
            </strong>
            <div class="citation-chips">
              <span
                v-for="(citation, idx) in message.citations"
                :key="idx"
                class="badge bg-info me-1 mb-1"
              >
                {{ citation }}
              </span>
            </div>
          </div>
          
          <!-- Metadata -->
          <div class="message-metadata mt-2">
            <small class="text-muted">
              <i class="bi bi-clock me-1"></i>
              {{ message.latency_ms }}ms
              <span class="mx-2">•</span>
              <i class="bi bi-arrow-down me-1"></i>
              {{ message.tokens_in }} tokens
              <span class="mx-2">•</span>
              <i class="bi bi-arrow-up me-1"></i>
              {{ message.tokens_out }} tokens
            </small>
          </div>
          
          <!-- Copy button -->
          <button
            class="btn btn-sm btn-outline-secondary mt-2"
            @click="copyToClipboard"
          >
            <i class="bi bi-clipboard me-1"></i>
            Copy
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const avatarIcon = computed(() => {
  if (props.message.role === 'user') return 'bi bi-person-circle'
  if (props.message.role === 'assistant') return 'bi bi-robot'
  return 'bi bi-exclamation-triangle'
})

const roleLabel = computed(() => {
  if (props.message.role === 'user') return 'You'
  if (props.message.role === 'assistant') return 'AI Assistant'
  return 'Error'
})

const formattedTime = computed(() => {
  return new Date(props.message.timestamp).toLocaleTimeString()
})

const formattedContent = computed(() => {
  // Convert markdown-style formatting to HTML
  let content = props.message.content
  
  // Bold
  content = content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  
  // Line breaks
  content = content.replace(/\n/g, '<br>')
  
  return content
})

const copyToClipboard = () => {
  navigator.clipboard.writeText(props.message.content)
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.chat-message.user .message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.chat-message.assistant .message-avatar {
  background: #f8f9fa;
  color: #495057;
}

.chat-message.error .message-avatar {
  background: #dc3545;
  color: white;
}

.message-content {
  flex: 1;
  min-width: 0;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.message-body {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 12px;
}

.chat-message.user .message-body {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-text {
  line-height: 1.6;
}

.citations {
  padding-top: 1rem;
  border-top: 1px solid #dee2e6;
}

.citation-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.message-metadata {
  padding-top: 0.5rem;
  border-top: 1px solid #dee2e6;
}
</style>