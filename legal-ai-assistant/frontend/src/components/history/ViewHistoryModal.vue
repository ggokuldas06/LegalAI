<!-- src/components/history/ViewHistoryModal.vue -->
<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
    <div class="modal-dialog modal-xl modal-dialog-scrollable">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <span :class="`badge bg-${modeColor} me-2`">Mode {{ chat?.mode }}</span>
            Chat Details
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>
        
        <div class="modal-body">
          <div v-if="chat">
            <!-- Metadata -->
            <div class="chat-metadata mb-4 p-3 bg-light rounded">
              <div class="row">
                <div class="col-md-6">
                  <strong>Date:</strong> {{ formatDate(chat.created_at) }}
                </div>
                <div class="col-md-6">
                  <strong>Mode:</strong> {{ modeLabel }}
                </div>
                <div class="col-md-4">
                  <strong>Tokens In:</strong> {{ chat.tokens_in }}
                </div>
                <div class="col-md-4">
                  <strong>Tokens Out:</strong> {{ chat.tokens_out }}
                </div>
                <div class="col-md-4">
                  <strong>Latency:</strong> {{ chat.latency_ms }}ms
                </div>
              </div>
            </div>
            
            <!-- Prompt -->
            <div class="chat-section mb-4">
              <h6 class="fw-bold">
                <i class="bi bi-person-circle me-2"></i>
                Your Question
              </h6>
              <div class="chat-content user-content p-3 rounded">
                {{ chat.prompt }}
              </div>
            </div>
            
            <!-- Response -->
            <div class="chat-section mb-4">
              <h6 class="fw-bold">
                <i class="bi bi-robot me-2"></i>
                AI Response
              </h6>
              <div class="chat-content assistant-content p-3 rounded">
                <pre class="mb-0">{{ chat.response }}</pre>
              </div>
            </div>
            
            <!-- Citations -->
            <div v-if="chat.citations && chat.citations.length > 0" class="chat-section mb-4">
              <h6 class="fw-bold">
                <i class="bi bi-quote me-2"></i>
                Citations ({{ chat.citations.length }})
              </h6>
              <div class="citations-list">
                <span
                  v-for="(citation, idx) in chat.citations"
                  :key="idx"
                  class="badge bg-info me-2 mb-2"
                >
                  {{ citation }}
                </span>
              </div>
            </div>
            
            <!-- Filters Used (Mode C) -->
            <div v-if="chat.mode === 'C' && hasFilters" class="chat-section">
              <h6 class="fw-bold">
                <i class="bi bi-funnel me-2"></i>
                Filters Used
              </h6>
              <div class="filters-display p-3 bg-light rounded">
                <div v-if="chat.filters_used.jurisdiction">
                  <strong>Jurisdiction:</strong> {{ chat.filters_used.jurisdiction }}
                </div>
                <div v-if="chat.filters_used.year_from || chat.filters_used.year_to">
                  <strong>Year Range:</strong>
                  {{ chat.filters_used.year_from || '—' }} to {{ chat.filters_used.year_to || '—' }}
                </div>
                <div v-if="chat.filters_used.include && chat.filters_used.include.length > 0">
                  <strong>Include:</strong> {{ chat.filters_used.include.join(', ') }}
                </div>
                <div v-if="chat.filters_used.exclude && chat.filters_used.exclude.length > 0">
                  <strong>Exclude:</strong> {{ chat.filters_used.exclude.join(', ') }}
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-secondary"
            @click="copyResponse"
          >
            <i class="bi bi-clipboard me-2"></i>
            Copy Response
          </button>
          <button type="button" class="btn btn-primary" @click="$emit('close')">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  chat: {
    type: Object,
    default: null,
  },
})

defineEmits(['close'])

const modeColor = computed(() => {
  const colors = { A: 'primary', B: 'success', C: 'info' }
  return colors[props.chat?.mode] || 'secondary'
})

const modeLabel = computed(() => {
  const labels = {
    A: 'Summarizer',
    B: 'Clause Classifier',
    C: 'Case-Law IRAC',
  }
  return labels[props.chat?.mode] || 'Unknown'
})

const hasFilters = computed(() => {
  if (!props.chat?.filters_used) return false
  const filters = props.chat.filters_used
  return filters.jurisdiction || filters.year_from || filters.year_to ||
         (filters.include && filters.include.length > 0) ||
         (filters.exclude && filters.exclude.length > 0)
})

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString()
}

const copyResponse = () => {
  if (props.chat?.response) {
    navigator.clipboard.writeText(props.chat.response)
    alert('Response copied to clipboard!')
  }
}
</script>

<style scoped>
.modal.show {
  display: block;
}

.chat-metadata {
  border-left: 4px solid #0d6efd;
}

.chat-section {
  margin-bottom: 1.5rem;
}

.user-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.assistant-content {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
}

.assistant-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
}

.citations-list {
  display: flex;
  flex-wrap: wrap;
}

.filters-display > div {
  margin-bottom: 0.5rem;
}
</style>