<!-- src/components/document/ViewDocumentModal.vue -->
<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
    <div class="modal-dialog modal-xl modal-dialog-scrollable">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="bi bi-eye me-2"></i>
            {{ document?.title }}
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>
        
        <div class="modal-body">
          <div v-if="loading" class="text-center py-5">
            <div class="spinner-border text-primary" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 text-muted">Loading document content...</p>
          </div>
          
          <div v-else-if="error" class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>
            {{ error }}
          </div>
          
          <div v-else>
            <!-- Document Info -->
            <div class="document-info mb-4 p-3 bg-light rounded">
              <div class="row">
                <div class="col-md-6">
                  <strong>Type:</strong>
                  <span class="badge bg-primary ms-2">{{ document?.doctype }}</span>
                </div>
                <div class="col-md-6" v-if="document?.jurisdiction">
                  <strong>Jurisdiction:</strong> {{ document.jurisdiction }}
                </div>
                <div class="col-md-6" v-if="document?.date">
                  <strong>Date:</strong> {{ formatDate(document.date) }}
                </div>
                <div class="col-md-6" v-if="document?.source">
                  <strong>Source:</strong> {{ document.source }}
                </div>
                <div class="col-md-12 mt-2">
                  <strong>Length:</strong> {{ contentLength.toLocaleString() }} characters
                </div>
              </div>
            </div>
            
            <!-- Document Content -->
            <div class="document-content">
              <pre class="content-pre">{{ content }}</pre>
            </div>
          </div>
        </div>
        
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-secondary"
            @click="copyContent"
            :disabled="!content"
          >
            <i class="bi bi-clipboard me-2"></i>
            Copy Content
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
import { ref, watch, computed } from 'vue'
import { useDocumentStore } from '@/stores/documents'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  document: {
    type: Object,
    default: null,
  },
})

defineEmits(['close'])

const documentStore = useDocumentStore()

const loading = ref(false)
const error = ref('')
const content = ref('')

const contentLength = computed(() => content.value?.length || 0)

const loadContent = async () => {
  if (!props.document) return
  
  loading.value = true
  error.value = ''
  content.value = ''
  
  try {
    const result = await documentStore.getDocumentContent(props.document.id)
    if (result.success) {
      content.value = result.data.content
    } else {
      error.value = result.error
    }
  } catch (err) {
    error.value = err.message || 'Failed to load document content'
  } finally {
    loading.value = false
  }
}

const copyContent = () => {
  if (content.value) {
    navigator.clipboard.writeText(content.value)
    alert('Content copied to clipboard!')
  }
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString()
}

watch(() => props.show, (newVal) => {
  if (newVal && props.document) {
    loadContent()
  }
})
</script>

<style scoped>
.modal.show {
  display: block;
}

.document-info {
  border-left: 4px solid #0d6efd;
}

.document-content {
  max-height: 60vh;
  overflow-y: auto;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 1rem;
  background: #f8f9fa;
}

.content-pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  margin: 0;
}
</style>