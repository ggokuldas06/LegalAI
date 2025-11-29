<!-- src/components/history/HistoryItem.vue -->
<template>
  <div class="history-item card mb-3">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start">
        <div class="flex-grow-1">
          <div class="d-flex align-items-center mb-2">
            <span :class="`badge bg-${modeColor} me-2`">Mode {{ chat.mode }}</span>
            <small class="text-muted">
              <i class="bi bi-clock me-1"></i>
              {{ formatDate(chat.created_at) }}
            </small>
          </div>
          
          <h6 class="mb-2">{{ truncateText(chat.prompt, 100) }}</h6>
          
          <div class="response-preview text-muted small">
            {{ truncateText(chat.response, 150) }}
          </div>
          
          <div class="metadata mt-2">
            <small class="text-muted">
              <i class="bi bi-arrow-down me-1"></i>
              {{ chat.tokens_in }} tokens in
              <span class="mx-2">•</span>
              <i class="bi bi-arrow-up me-1"></i>
              {{ chat.tokens_out }} tokens out
              <span class="mx-2">•</span>
              <i class="bi bi-clock me-1"></i>
              {{ chat.latency_ms }}ms
              <span v-if="chat.citations && chat.citations.length > 0" class="mx-2">•</span>
              <span v-if="chat.citations && chat.citations.length > 0">
                <i class="bi bi-quote me-1"></i>
                {{ chat.citations.length }} citations
              </span>
            </small>
          </div>
        </div>
        
        <div class="btn-group-vertical ms-3">
          <button
            class="btn btn-sm btn-outline-primary"
            @click="$emit('view', chat)"
            title="View"
          >
            <i class="bi bi-eye"></i>
          </button>
          <button
            class="btn btn-sm btn-outline-danger"
            @click="$emit('delete', chat.id)"
            title="Delete"
          >
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  chat: {
    type: Object,
    required: true,
  },
})

defineEmits(['view', 'delete'])

const modeColor = computed(() => {
  const colors = { A: 'primary', B: 'success', C: 'info' }
  return colors[props.chat.mode] || 'secondary'
})

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  
  // Less than 1 minute
  if (diff < 60000) {
    return 'Just now'
  }
  // Less than 1 hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes} minute${minutes > 1 ? 's' : ''} ago`
  }
  // Less than 1 day
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000)
    return `${hours} hour${hours > 1 ? 's' : ''} ago`
  }
  // More than 1 day
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
</script>

<style scoped>
.history-item {
  transition: transform 0.2s, box-shadow 0.2s;
}

.history-item:hover {
  transform: translateX(4px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.response-preview {
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.metadata {
  padding-top: 0.5rem;
  border-top: 1px solid #dee2e6;
}
</style>