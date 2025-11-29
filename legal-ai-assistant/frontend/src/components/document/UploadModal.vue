<!-- src/components/document/UploadModal.vue -->
<template>
  <div v-if="show" class="modal fade show d-block" tabindex="-1" style="background: rgba(0,0,0,0.5)">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <i class="bi bi-upload me-2"></i>
            Upload Document
          </h5>
          <button type="button" class="btn-close" @click="handleClose"></button>
        </div>
        
        <div class="modal-body">
          <AlertMessage
            :show="!!error"
            type="danger"
            :message="error"
            @close="error = ''"
          />
          
          <form @submit.prevent="handleUpload">
            <!-- File Upload -->
            <div class="mb-3">
              <label class="form-label">File *</label>
              <input
                ref="fileInput"
                type="file"
                class="form-control"
                accept=".pdf,.txt"
                @change="handleFileSelect"
                required
              >
              <small class="text-muted">Supported: PDF, TXT (Max 10MB)</small>
            </div>
            
            <div v-if="selectedFile" class="file-preview mb-3">
              <i class="bi bi-file-earmark-text me-2"></i>
              <strong>{{ selectedFile.name }}</strong>
              <small class="text-muted ms-2">({{ formatFileSize(selectedFile.size) }})</small>
            </div>
            
            <!-- Document Type -->
            <div class="mb-3">
              <label class="form-label">Document Type *</label>
              <select v-model="formData.doctype" class="form-select" required>
                <option value="">Select type...</option>
                <option value="contract">Contract</option>
                <option value="case">Case Law</option>
                <option value="regulation">Regulation</option>
                <option value="statute">Statute</option>
                <option value="other">Other</option>
              </select>
            </div>
            
            <!-- Title -->
            <div class="mb-3">
              <label class="form-label">Title *</label>
              <input
                v-model="formData.title"
                type="text"
                class="form-control"
                placeholder="Enter document title"
                required
              >
            </div>
            
            <!-- Jurisdiction -->
            <div class="mb-3">
              <label class="form-label">Jurisdiction</label>
              <select v-model="formData.jurisdiction" class="form-select">
                <option value="">Select jurisdiction...</option>
                <option value="US">United States</option>
                <option value="US-CA">US - California</option>
                <option value="US-NY">US - New York</option>
                <option value="US-TX">US - Texas</option>
                <option value="EU">European Union</option>
                <option value="UK">United Kingdom</option>
                <option value="UK-ENG">UK - England</option>
                <option value="UK-SCT">UK - Scotland</option>
              </select>
            </div>
            
            <!-- Date -->
            <div class="mb-3">
              <label class="form-label">Date</label>
              <input
                v-model="formData.date"
                type="date"
                class="form-control"
              >
            </div>
            
            <!-- Source -->
            <div class="mb-3">
              <label class="form-label">Source</label>
              <input
                v-model="formData.source"
                type="text"
                class="form-control"
                placeholder="e.g., Court website, Contract repository"
              >
            </div>
            
            <!-- Upload Progress -->
            <div v-if="isUploading" class="mb-3">
              <div class="progress">
                <div
                  class="progress-bar progress-bar-striped progress-bar-animated"
                  role="progressbar"
                  :style="{ width: uploadProgress + '%' }"
                >
                  {{ uploadProgress }}%
                </div>
              </div>
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-secondary"
            @click="handleClose"
            :disabled="isUploading"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary"
            @click="handleUpload"
            :disabled="!canUpload || isUploading"
          >
            <span v-if="isUploading" class="spinner-border spinner-border-sm me-2"></span>
            {{ isUploading ? 'Uploading...' : 'Upload' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDocumentStore } from '@/stores/documents'
import AlertMessage from '@/components/common/AlertMessage.vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'uploaded'])

const documentStore = useDocumentStore()

const fileInput = ref(null)
const selectedFile = ref(null)
const isUploading = ref(false)
const uploadProgress = ref(0)
const error = ref('')

const formData = ref({
  doctype: '',
  title: '',
  jurisdiction: '',
  date: '',
  source: '',
})

const canUpload = computed(() => {
  return selectedFile.value && formData.value.doctype && formData.value.title
})

const handleFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    // Validate file size (10MB max)
    if (file.size > 10 * 1024 * 1024) {
      error.value = 'File size must be less than 10MB'
      fileInput.value.value = ''
      return
    }
    
    // Validate file type
    const validTypes = ['application/pdf', 'text/plain']
    if (!validTypes.includes(file.type)) {
      error.value = 'Only PDF and TXT files are supported'
      fileInput.value.value = ''
      return
    }
    
    selectedFile.value = file
    error.value = ''
    
    // Auto-fill title if empty
    if (!formData.value.title) {
      formData.value.title = file.name.replace(/\.[^/.]+$/, '')
    }
  }
}

const handleUpload = async () => {
  if (!canUpload.value) return
  
  isUploading.value = true
  uploadProgress.value = 0
  error.value = ''
  
  // Simulate progress (in real implementation, track actual upload progress)
  const progressInterval = setInterval(() => {
    if (uploadProgress.value < 90) {
      uploadProgress.value += 10
    }
  }, 200)
  
  try {
    const result = await documentStore.uploadDocument(
      selectedFile.value,
      formData.value
    )
    
    clearInterval(progressInterval)
    uploadProgress.value = 100
    
    if (result.success) {
      setTimeout(() => {
        emit('uploaded', result.document)
        resetForm()
      }, 500)
    } else {
      error.value = result.error
    }
  } catch (err) {
    clearInterval(progressInterval)
    error.value = err.message || 'Upload failed'
  } finally {
    isUploading.value = false
  }
}

const handleClose = () => {
  if (!isUploading.value) {
    resetForm()
    emit('close')
  }
}

const resetForm = () => {
  selectedFile.value = null
  formData.value = {
    doctype: '',
    title: '',
    jurisdiction: '',
    date: '',
    source: '',
  }
  error.value = ''
  uploadProgress.value = 0
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.modal.show {
  display: block;
}

.file-preview {
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  display: flex;
  align-items: center;
}

.progress {
  height: 25px;
}
</style>