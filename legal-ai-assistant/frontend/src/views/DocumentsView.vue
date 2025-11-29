<!-- src/views/DocumentsView.vue -->
<template>
  <div class="documents-view container py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>
        <i class="bi bi-folder2-open me-2"></i>
        Documents
      </h2>
      <button class="btn btn-primary" @click="showUploadModal = true">
        <i class="bi bi-upload me-2"></i>
        Upload Document
      </button>
    </div>
    
    <AlertMessage
      :show="!!alert.message"
      :type="alert.type"
      :message="alert.message"
      @close="alert.message = ''"
    />
    
    <!-- Filters -->
    <div class="row mb-4">
      <div class="col-md-4">
        <select v-model="filterType" class="form-select" @change="fetchDocuments">
          <option value="">All Types</option>
          <option value="contract">Contract</option>
          <option value="case">Case Law</option>
          <option value="regulation">Regulation</option>
          <option value="statute">Statute</option>
          <option value="other">Other</option>
        </select>
      </div>
    </div>
    
    <!-- Documents List -->
    <LoadingSpinner v-if="documentStore.isLoading" message="Loading documents..." />
    
    <div v-else-if="documentStore.documents.length === 0" class="empty-state text-center py-5">
      <i class="bi bi-inbox display-1 text-muted"></i>
      <h4 class="mt-3">No Documents Yet</h4>
      <p class="text-muted">Upload your first document to get started</p>
      <button class="btn btn-primary" @click="showUploadModal = true">
        <i class="bi bi-upload me-2"></i>
        Upload Document
      </button>
    </div>
    
    <div v-else class="row g-4">
      <div
        v-for="doc in documentStore.documents"
        :key="doc.id"
        class="col-md-4"
      >
        <DocumentCard
          :document="doc"
          @delete="handleDelete"
          @ingest="handleIngest"
          @view="handleView"
        />
      </div>
    </div>
    
    <!-- Upload Modal -->
    <UploadModal
      :show="showUploadModal"
      @close="showUploadModal = false"
      @uploaded="handleUploaded"
    />
    
    <!-- View Modal -->
    <ViewDocumentModal
      :show="showViewModal"
      :document="currentDocument"
      @close="showViewModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDocumentStore } from '@/stores/documents'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import AlertMessage from '@/components/common/AlertMessage.vue'
import DocumentCard from '@/components/document/DocumentCard.vue'
import UploadModal from '@/components/document/UploadModal.vue'
import ViewDocumentModal from '@/components/document/ViewDocumentModal.vue'

const documentStore = useDocumentStore()

const showUploadModal = ref(false)
const showViewModal = ref(false)
const currentDocument = ref(null)
const filterType = ref('')
const alert = ref({ type: 'info', message: '' })

const fetchDocuments = async () => {
  const params = {}
  if (filterType.value) {
    params.doctype = filterType.value
  }
  await documentStore.fetchDocuments(params)
}

const handleDelete = async (docId) => {
  if (confirm('Are you sure you want to delete this document?')) {
    const result = await documentStore.deleteDocument(docId)
    if (result.success) {
      alert.value = { type: 'success', message: 'Document deleted successfully' }
    } else {
      alert.value = { type: 'danger', message: result.error }
    }
  }
}

const handleIngest = async (docId) => {
  const result = await documentStore.ingestDocument(docId)
  if (result.success) {
    alert.value = {
      type: 'success',
      message: `Document ingested! Created ${result.data.chunks_created} chunks`,
    }
  } else {
    alert.value = { type: 'danger', message: result.error }
  }
}

const handleView = (doc) => {
  currentDocument.value = doc
  showViewModal.value = true
}

const handleUploaded = () => {
  showUploadModal.value = false
  fetchDocuments()
  alert.value = { type: 'success', message: 'Document uploaded successfully' }
}

onMounted(() => {
  fetchDocuments()
})
</script>

<style scoped>
.documents-view {
  min-height: calc(100vh - 56px);
}

.empty-state {
  background: white;
  border-radius: 12px;
  padding: 3rem;
}
</style>