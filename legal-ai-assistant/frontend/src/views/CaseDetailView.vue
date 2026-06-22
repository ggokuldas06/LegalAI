<!-- src/views/CaseDetailView.vue -->
<template>
  <div class="case-detail container-fluid py-4">
    <!-- Loading -->
    <div v-if="casesStore.isLoading && !casesStore.currentCase" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <template v-else-if="casesStore.currentCase">
      <!-- Header -->
      <div class="d-flex justify-content-between align-items-start mb-4">
        <div>
          <router-link to="/cases" class="text-muted small">
            <i class="bi bi-arrow-left me-1"></i>All Cases
          </router-link>
          <h4 class="mt-1 mb-0">
            <i class="bi bi-briefcase me-2"></i>
            <span v-if="!editingTitle">{{ casesStore.currentCase.title }}</span>
            <input v-else v-model="editTitle" class="form-control d-inline-block w-auto" style="font-size:1.3rem"
              @keydown.enter="saveTitle" @keydown.esc="editingTitle = false" />
            <button v-if="!editingTitle" class="btn btn-sm btn-link ms-2" @click="startEditTitle">
              <i class="bi bi-pencil"></i>
            </button>
            <button v-else class="btn btn-sm btn-success ms-1" @click="saveTitle">Save</button>
          </h4>
          <p v-if="casesStore.currentCase.description" class="text-muted mt-1 mb-0">
            {{ casesStore.currentCase.description }}
          </p>
        </div>
        <router-link :to="`/chat?mode=D&case=${casesStore.currentCase.id}`" class="btn btn-primary">
          <i class="bi bi-robot me-2"></i>Ask Agent
        </router-link>
      </div>

      <!-- Stats bar -->
      <div class="stats-bar mb-4 d-flex gap-3">
        <span class="badge bg-primary-subtle text-primary px-3 py-2">
          <i class="bi bi-file-earmark me-1"></i>{{ casesStore.currentCase.document_count }} documents
        </span>
        <span class="badge bg-secondary-subtle text-secondary px-3 py-2">
          <i class="bi bi-calendar me-1"></i>Updated {{ formatDate(casesStore.currentCase.updated_at) }}
        </span>
      </div>

      <!-- Add documents section -->
      <div class="card mb-4">
        <div class="card-header d-flex justify-content-between align-items-center">
          <strong><i class="bi bi-plus-circle me-2"></i>Add Documents</strong>
          <button class="btn btn-sm btn-outline-primary" @click="showAddDocs = !showAddDocs">
            {{ showAddDocs ? 'Cancel' : 'Select Documents' }}
          </button>
        </div>

        <div v-if="showAddDocs" class="card-body">
          <div v-if="docsStore.isLoading" class="text-muted small">Loading documents…</div>
          <div v-else>
            <div class="mb-2">
              <input v-model="docSearch" class="form-control form-control-sm" placeholder="Filter documents…" />
            </div>
            <div class="doc-pick-list">
              <div
                v-for="doc in filteredDocs"
                :key="doc.id"
                class="doc-pick-item d-flex align-items-center gap-2 p-2 rounded"
                :class="{ selected: selectedDocIds.includes(doc.id), 'already-in': isInCase(doc.id) }"
                @click="!isInCase(doc.id) && toggleDoc(doc.id)"
              >
                <i :class="fileIcon(doc.file_type)" class="fs-5"></i>
                <div class="flex-1">
                  <div class="fw-medium">{{ doc.title }}</div>
                  <small class="text-muted">{{ doc.doctype }} • {{ doc.file_type?.toUpperCase() }}
                    <span v-if="doc.page_count"> • {{ doc.page_count }}p</span>
                    <span v-if="doc.has_description" class="text-success ms-1">
                      <i class="bi bi-check-circle-fill"></i> described
                    </span>
                  </small>
                </div>
                <i v-if="isInCase(doc.id)" class="bi bi-check-circle-fill text-success ms-auto"></i>
                <input v-else type="checkbox" :checked="selectedDocIds.includes(doc.id)"
                  @click.stop="toggleDoc(doc.id)" />
              </div>
            </div>

            <div class="mt-3 d-flex gap-2 align-items-center">
              <select v-model="addRole" class="form-select form-select-sm w-auto">
                <option value="other">Role: Other</option>
                <option value="primary">Primary Document</option>
                <option value="evidence">Evidence</option>
                <option value="reference">Reference</option>
                <option value="contract">Contract</option>
                <option value="exhibit">Exhibit</option>
              </select>
              <button class="btn btn-primary btn-sm" :disabled="!selectedDocIds.length || adding"
                @click="addDocuments">
                <span v-if="adding"><span class="spinner-border spinner-border-sm me-1"></span>Adding…</span>
                <span v-else>Add {{ selectedDocIds.length }} document(s)</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Documents in case -->
      <div class="card">
        <div class="card-header">
          <strong><i class="bi bi-files me-2"></i>Documents in Case</strong>
        </div>
        <div v-if="casesStore.currentCase.case_documents.length === 0" class="card-body text-muted text-center py-4">
          No documents yet. Add documents above to start using Case Q&A.
        </div>
        <ul v-else class="list-group list-group-flush">
          <li
            v-for="cd in casesStore.currentCase.case_documents"
            :key="cd.id"
            class="list-group-item d-flex align-items-center gap-3"
          >
            <i :class="fileIcon(cd.document.file_type)" class="fs-5 text-secondary"></i>
            <div class="flex-1">
              <div class="fw-medium">{{ cd.document.title }}</div>
              <small class="text-muted">
                {{ cd.document.doctype }} •
                <span class="badge" :class="roleClass(cd.role)">{{ cd.role }}</span>
                <span v-if="cd.document.page_count" class="ms-2">{{ cd.document.page_count }}p</span>
                <span v-if="cd.document.has_description" class="text-success ms-2">
                  <i class="bi bi-check-circle-fill"></i> routing description ready
                </span>
                <span v-else class="text-warning ms-2">
                  <i class="bi bi-exclamation-circle"></i> no description (ingest to generate)
                </span>
              </small>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-secondary" title="Ingest document"
                @click="ingestDoc(cd.document.id)">
                <i class="bi bi-database-fill-up"></i>
              </button>
              <button class="btn btn-sm btn-outline-danger" @click="removeDoc(cd.document.id)">
                <i class="bi bi-x-lg"></i>
              </button>
            </div>
          </li>
        </ul>
      </div>
    </template>

    <div v-else class="text-center py-5 text-muted">
      <i class="bi bi-exclamation-triangle display-4"></i>
      <p class="mt-3">Case not found.</p>
      <router-link to="/cases" class="btn btn-outline-secondary">Back to Cases</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCasesStore } from '@/stores/cases'
import { useDocumentStore as useDocumentsStore } from '@/stores/documents'
import { ragAPI } from '@/services/api'

const route = useRoute()
const router = useRouter()
const casesStore = useCasesStore()
const docsStore = useDocumentsStore()

const caseId = parseInt(route.params.id)

// Edit title
const editingTitle = ref(false)
const editTitle = ref('')
const startEditTitle = () => {
  editTitle.value = casesStore.currentCase?.title ?? ''
  editingTitle.value = true
}
const saveTitle = async () => {
  if (!editTitle.value.trim()) return
  await casesStore.updateCase(caseId, { title: editTitle.value.trim() })
  editingTitle.value = false
}

// Add docs panel
const showAddDocs = ref(false)
const docSearch = ref('')
const selectedDocIds = ref([])
const addRole = ref('other')
const adding = ref(false)

const filteredDocs = computed(() => {
  const q = docSearch.value.toLowerCase()
  return (docsStore.documents || []).filter((d) =>
    !q || d.title.toLowerCase().includes(q) || d.doctype.toLowerCase().includes(q)
  )
})

const isInCase = (docId) =>
  casesStore.currentCase?.case_documents?.some((cd) => cd.document.id === docId) ?? false

const toggleDoc = (id) => {
  const idx = selectedDocIds.value.indexOf(id)
  if (idx === -1) selectedDocIds.value.push(id)
  else selectedDocIds.value.splice(idx, 1)
}

const addDocuments = async () => {
  adding.value = true
  try {
    await casesStore.addDocuments(caseId, selectedDocIds.value, addRole.value)
    selectedDocIds.value = []
    showAddDocs.value = false
  } finally {
    adding.value = false
  }
}

const removeDoc = async (docId) => {
  if (!confirm('Remove this document from the case?')) return
  await casesStore.removeDocument(caseId, docId)
}

const ingestDoc = async (docId) => {
  try {
    await ragAPI.ingest(docId)
    alert('Ingestion triggered. Refresh in a moment to see updated description status.')
  } catch (e) {
    alert('Ingest error: ' + (e.response?.data?.error || e.message))
  }
}

const fileIcon = (ft) => {
  if (ft === 'image') return 'bi bi-image'
  if (ft === 'pdf') return 'bi bi-file-earmark-pdf text-danger'
  return 'bi bi-file-earmark-text'
}

const roleClass = (role) => {
  const map = {
    primary: 'bg-primary text-white',
    evidence: 'bg-warning text-dark',
    reference: 'bg-info text-dark',
    contract: 'bg-success text-white',
    exhibit: 'bg-secondary text-white',
  }
  return map[role] || 'bg-light text-dark'
}

const formatDate = (iso) => new Date(iso).toLocaleDateString()

onMounted(async () => {
  await casesStore.fetchCase(caseId)
  await docsStore.fetchDocuments()
})
</script>

<style scoped>
.doc-pick-list {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 0.5rem;
}
.doc-pick-item {
  cursor: pointer;
  transition: background 0.15s;
  border-radius: 6px;
}
.doc-pick-item:hover:not(.already-in) {
  background: #f0f4ff;
}
.doc-pick-item.selected {
  background: #dbeafe;
}
.doc-pick-item.already-in {
  cursor: default;
  opacity: 0.6;
}
.flex-1 { flex: 1; min-width: 0; }
.stats-bar { flex-wrap: wrap; }
</style>
