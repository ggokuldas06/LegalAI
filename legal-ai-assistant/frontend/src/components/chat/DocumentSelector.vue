<!-- src/components/chat/DocumentSelector.vue -->
<template>
  <div class="document-selector card">
    <div class="card-body">
      <h6 class="card-title">
        <i class="bi bi-file-earmark me-2"></i>
        Select Document
      </h6>
      
      <div v-if="documents.length === 0" class="text-center text-muted py-3">
        <i class="bi bi-inbox display-6"></i>
        <p class="mt-2">No documents available</p>
        <router-link to="/documents" class="btn btn-sm btn-primary">
          Upload Document
        </router-link>
      </div>

      <div v-else>
        <select
          v-model="selectedDocId"
          class="form-select"
          @change="handleSelect"
        >
          <option :value="null">Choose a document...</option>
          <option
            v-for="doc in documents"
            :key="doc.id"
            :value="doc.id"
          >
            {{ doc.title }} ({{ doc.doctype }})
          </option>
        </select>

        <div v-if="selectedDocument" class="selected-doc-info mt-3">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <strong>{{ selectedDocument.title }}</strong>
              <div class="text-muted small">
                <span class="badge bg-secondary me-2">{{ selectedDocument.doctype }}</span>
                <span v-if="selectedDocument.jurisdiction">{{ selectedDocument.jurisdiction }}</span>
              </div>
            </div>
            <button
              class="btn btn-sm btn-outline-danger"
              @click="clearSelection"
            >
              <i class="bi bi-x"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDocumentStore } from '@/stores/documents'

const props = defineProps({
  modelValue: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['update:modelValue'])

const documentStore = useDocumentStore()

const selectedDocId = ref(props.modelValue?.id || null)

const documents = computed(() => documentStore.documents)
const selectedDocument = computed(() =>
  documents.value.find((doc) => doc.id === selectedDocId.value)
)

const handleSelect = () => {
  const doc = documents.value.find((d) => d.id === selectedDocId.value)
  emit('update:modelValue', doc || null)
}

const clearSelection = () => {
  selectedDocId.value = null
  emit('update:modelValue', null)
}

onMounted(async () => {
  if (documents.value.length === 0) {
    await documentStore.fetchDocuments()
  }
})
</script>

<style scoped>
.document-selector {
  margin-bottom: 1.5rem;
}

.selected-doc-info {
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
}
</style>