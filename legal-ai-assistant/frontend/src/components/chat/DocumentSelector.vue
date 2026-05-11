<!-- src/components/chat/DocumentSelector.vue -->
<template>
  <div class="document-selector card">
    <div class="card-body">
      <h6 class="card-title mb-1">
        <i class="bi bi-file-earmark me-2"></i>
        {{ label }}
        <span v-if="!isRequired" class="text-muted fw-normal small ms-1">(optional)</span>
      </h6>

      <div v-if="documents.length === 0" class="text-center text-muted py-3">
        <i class="bi bi-inbox display-6"></i>
        <p class="mt-2 mb-1">No documents uploaded yet</p>
        <router-link to="/documents" class="btn btn-sm btn-primary">
          Upload Document
        </router-link>
      </div>

      <div v-else>
        <select v-model="selectedDocId" class="form-select" @change="handleSelect">
          <option :value="null">{{ isRequired ? 'Choose a document…' : 'All documents (global search)' }}</option>
          <option v-for="doc in documents" :key="doc.id" :value="doc.id">
            {{ doc.title }}
            {{ doc.chunk_count > 0 ? `(${doc.chunk_count} chunks)` : '(not indexed)' }}
          </option>
        </select>

        <!-- Selected document info -->
        <div v-if="selectedDocument" class="selected-doc-info mt-2">
          <div class="d-flex justify-content-between align-items-start gap-2">
            <div class="flex-grow-1 min-w-0">
              <div class="fw-semibold text-truncate">{{ selectedDocument.title }}</div>
              <div class="d-flex align-items-center gap-1 mt-1 flex-wrap">
                <span class="badge bg-secondary">{{ selectedDocument.doctype }}</span>
                <span v-if="selectedDocument.jurisdiction" class="badge bg-light text-dark border">
                  {{ selectedDocument.jurisdiction }}
                </span>
                <span
                  v-if="selectedDocument.chunk_count > 0"
                  class="badge bg-success"
                >
                  {{ selectedDocument.chunk_count }} chunks indexed
                </span>
                <span v-else class="badge bg-warning text-dark">Not indexed</span>
              </div>
            </div>
            <button class="btn btn-sm btn-outline-danger flex-shrink-0" @click="clearSelection">
              <i class="bi bi-x"></i>
            </button>
          </div>

          <!-- Ingest button — show when doc is not indexed (relevant for all modes) -->
          <div v-if="selectedDocument.chunk_count === 0" class="mt-2">
            <div v-if="mode === 'C'" class="alert alert-warning py-2 px-3 mb-2 small">
              This document hasn't been indexed yet. IRAC mode needs indexed chunks to search.
            </div>
            <button
              class="btn btn-sm btn-primary w-100"
              :disabled="ingesting"
              @click="handleIngest"
            >
              <span v-if="ingesting">
                <span class="spinner-border spinner-border-sm me-1"></span>
                Indexing…
              </span>
              <span v-else>
                <i class="bi bi-lightning-charge me-1"></i>
                Index this document
              </span>
            </button>
            <div v-if="ingestError" class="text-danger small mt-1">{{ ingestError }}</div>
          </div>
        </div>

        <!-- Mode C hint when no document selected -->
        <div v-if="mode === 'C' && !selectedDocument" class="mt-2 text-muted small">
          <i class="bi bi-info-circle me-1"></i>
          No filter — searches across all indexed documents.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDocumentStore } from '@/stores/documents'

const props = defineProps({
  modelValue: { type: Object, default: null },
  mode: { type: String, default: null },
  isRequired: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue'])

const documentStore = useDocumentStore()
const selectedDocId = ref(props.modelValue?.id ?? null)
const ingesting = ref(false)
const ingestError = ref('')

const documents = computed(() => documentStore.documents)

const selectedDocument = computed(() =>
  documents.value.find((doc) => doc.id === selectedDocId.value) ?? null
)

const label = computed(() => {
  if (props.mode === 'A') return 'Document to Summarize'
  if (props.mode === 'B') return 'Document to Classify'
  if (props.mode === 'C') return 'Filter to Document'
  return 'Select Document'
})

const handleSelect = () => {
  const doc = documents.value.find((d) => d.id === selectedDocId.value) ?? null
  ingestError.value = ''
  emit('update:modelValue', doc)
}

const clearSelection = () => {
  selectedDocId.value = null
  ingestError.value = ''
  emit('update:modelValue', null)
}

const handleIngest = async () => {
  if (!selectedDocument.value) return
  ingesting.value = true
  ingestError.value = ''
  const result = await documentStore.ingestDocument(selectedDocument.value.id)
  ingesting.value = false
  if (!result.success) {
    ingestError.value = result.error || 'Indexing failed'
  }
}

onMounted(async () => {
  if (documents.value.length === 0) {
    await documentStore.fetchDocuments()
  }
})
</script>

<style scoped>
.document-selector {
  margin-bottom: 0;
}

.selected-doc-info {
  padding: 0.65rem 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.min-w-0 {
  min-width: 0;
}
</style>
