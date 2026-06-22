<!-- src/views/CasesView.vue -->
<template>
  <div class="cases-view container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="mb-0">
        <i class="bi bi-briefcase me-2"></i>Cases
      </h4>
      <button class="btn btn-primary" @click="showCreate = true">
        <i class="bi bi-plus-lg me-2"></i>New Case
      </button>
    </div>

    <!-- Loading -->
    <div v-if="casesStore.isLoading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <!-- Empty -->
    <div v-else-if="casesStore.cases.length === 0" class="empty-state text-center py-5">
      <i class="bi bi-briefcase display-1 text-muted"></i>
      <h5 class="mt-3">No cases yet</h5>
      <p class="text-muted">Create a case to group documents and images for agentic Q&A.</p>
      <button class="btn btn-primary" @click="showCreate = true">
        <i class="bi bi-plus-lg me-2"></i>Create First Case
      </button>
    </div>

    <!-- Cases grid -->
    <div v-else class="row g-3">
      <div v-for="c in casesStore.cases" :key="c.id" class="col-md-6 col-lg-4">
        <div class="card h-100 case-card" @click="$router.push(`/cases/${c.id}`)">
          <div class="card-body">
            <h5 class="card-title">{{ c.title }}</h5>
            <p v-if="c.description" class="card-text text-muted small">{{ c.description }}</p>
            <div class="d-flex align-items-center gap-3 mt-3">
              <span class="badge bg-primary-subtle text-primary">
                <i class="bi bi-file-earmark me-1"></i>{{ c.document_count }} docs
              </span>
              <small class="text-muted">{{ formatDate(c.updated_at) }}</small>
            </div>
          </div>
          <div class="card-footer d-flex justify-content-between align-items-center">
            <router-link :to="`/cases/${c.id}`" class="btn btn-sm btn-outline-primary">
              <i class="bi bi-folder-open me-1"></i>Open
            </router-link>
            <button class="btn btn-sm btn-outline-danger" @click.stop="confirmDelete(c)">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create modal -->
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal-box p-4">
        <h5 class="mb-3">New Case</h5>
        <div class="mb-3">
          <label class="form-label">Title <span class="text-danger">*</span></label>
          <input v-model="newTitle" class="form-control" placeholder="e.g. Smith v. Jones 2024" />
        </div>
        <div class="mb-3">
          <label class="form-label">Description</label>
          <textarea v-model="newDescription" class="form-control" rows="2"
            placeholder="Optional context about this case" />
        </div>
        <div class="d-flex gap-2 justify-content-end">
          <button class="btn btn-secondary" @click="showCreate = false">Cancel</button>
          <button class="btn btn-primary" :disabled="!newTitle.trim() || creating" @click="createCase">
            <span v-if="creating"><span class="spinner-border spinner-border-sm me-2"></span>Creating…</span>
            <span v-else>Create Case</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCasesStore } from '@/stores/cases'

const casesStore = useCasesStore()
const router = useRouter()

const showCreate = ref(false)
const newTitle = ref('')
const newDescription = ref('')
const creating = ref(false)

onMounted(() => casesStore.fetchCases())

const formatDate = (iso) => new Date(iso).toLocaleDateString()

const createCase = async () => {
  creating.value = true
  try {
    const c = await casesStore.createCase(newTitle.value.trim(), newDescription.value.trim())
    showCreate.value = false
    newTitle.value = ''
    newDescription.value = ''
    router.push(`/cases/${c.id}`)
  } finally {
    creating.value = false
  }
}

const confirmDelete = async (c) => {
  if (!confirm(`Delete case "${c.title}"? This does not delete the documents.`)) return
  await casesStore.deleteCase(c.id)
}
</script>

<style scoped>
.case-card {
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}
.case-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  transform: translateY(-2px);
}
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 1050;
}
.modal-box {
  background: white;
  border-radius: 12px;
  width: 100%; max-width: 500px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
}
</style>
