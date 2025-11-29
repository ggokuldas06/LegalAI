<!-- src/views/HistoryView.vue -->
<template>
  <div class="history-view container py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2>
        <i class="bi bi-clock-history me-2"></i>
        Chat History
      </h2>
      <button class="btn btn-outline-primary" @click="handleExport">
        <i class="bi bi-download me-2"></i>
        Export
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
      <div class="col-md-3">
        <select v-model="filterMode" class="form-select" @change="fetchHistory">
          <option value="">All Modes</option>
          <option value="A">Summarizer</option>
          <option value="B">Clause Classifier</option>
          <option value="C">Case-Law IRAC</option>
        </select>
      </div>
      <div class="col-md-6">
        <input
          v-model="searchQuery"
          type="text"
          class="form-control"
          placeholder="Search in prompts..."
          @input="debouncedSearch"
        >
      </div>
    </div>
    
    <!-- History List -->
    <LoadingSpinner v-if="historyStore.isLoading" message="Loading history..." />
    
    <div v-else-if="historyStore.history.length === 0" class="empty-state text-center py-5">
      <i class="bi bi-inbox display-1 text-muted"></i>
      <h4 class="mt-3">No Chat History</h4>
      <p class="text-muted">Your conversations will appear here</p>
      <router-link to="/chat" class="btn btn-primary">
        <i class="bi bi-chat-dots me-2"></i>
        Start Chatting
      </router-link>
    </div>
    
    <div v-else class="history-list">
      <HistoryItem
        v-for="chat in historyStore.history"
        :key="chat.id"
        :chat="chat"
        @view="handleView"
        @delete="handleDelete"
      />
      
      <!-- Pagination -->
      <div v-if="historyStore.total > limit" class="mt-4">
        <nav>
          <ul class="pagination justify-content-center">
            <li class="page-item" :class="{ disabled: offset === 0 }">
              <a class="page-link" href="#" @click.prevent="changePage(-1)">Previous</a>
            </li>
            <li class="page-item disabled">
              <span class="page-link">
                Page {{ currentPage }} of {{ totalPages }}
              </span>
            </li>
            <li class="page-item" :class="{ disabled: offset + limit >= historyStore.total }">
              <a class="page-link" href="#" @click.prevent="changePage(1)">Next</a>
            </li>
          </ul>
        </nav>
      </div>
    </div>
    
    <!-- View Modal -->
    <ViewHistoryModal
      :show="showViewModal"
      :chat="currentChat"
      @close="showViewModal = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useHistoryStore } from '@/stores/history'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import AlertMessage from '@/components/common/AlertMessage.vue'
import HistoryItem from '@/components/history/HistoryItem.vue'
import ViewHistoryModal from '@/components/history/ViewHistoryModal.vue'

const historyStore = useHistoryStore()

const filterMode = ref('')
const searchQuery = ref('')
const limit = ref(20)
const offset = ref(0)
const showViewModal = ref(false)
const currentChat = ref(null)
const alert = ref({ type: 'info', message: '' })

let searchTimeout = null

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1)
const totalPages = computed(() => Math.ceil(historyStore.total / limit.value))

const fetchHistory = async () => {
  const params = {
    limit: limit.value,
    offset: offset.value,
  }
  
  if (filterMode.value) {
    params.mode = filterMode.value
  }
  
  if (searchQuery.value) {
    params.search = searchQuery.value
  }
  
  await historyStore.fetchHistory(params)
}

const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    offset.value = 0
    fetchHistory()
  }, 500)
}

const changePage = (direction) => {
  const newOffset = offset.value + (direction * limit.value)
  if (newOffset >= 0 && newOffset < historyStore.total) {
    offset.value = newOffset
    fetchHistory()
  }
}

const handleView = async (chat) => {
  const result = await historyStore.getChat(chat.id)
  if (result.success) {
    currentChat.value = result.data
    showViewModal.value = true
  }
}

const handleDelete = async (chatId) => {
  if (confirm('Are you sure you want to delete this chat?')) {
    const result = await historyStore.deleteChat(chatId)
    if (result.success) {
      alert.value = { type: 'success', message: 'Chat deleted successfully' }
      fetchHistory()
    } else {
      alert.value = { type: 'danger', message: result.error }
    }
  }
}

const handleExport = async () => {
  const filters = {}
  if (filterMode.value) {
    filters.mode = filterMode.value
  }
  
  const result = await historyStore.exportHistory(filters)
  if (result.success) {
    // Create downloadable JSON file
    const dataStr = JSON.stringify(result.data, null, 2)
    const blob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `chat-history-${new Date().toISOString()}.json`
    link.click()
    URL.revokeObjectURL(url)
    
    alert.value = { type: 'success', message: 'History exported successfully' }
  } else {
    alert.value = { type: 'danger', message: result.error }
  }
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.history-view {
  min-height: calc(100vh - 56px);
}

.empty-state {
  background: white;
  border-radius: 12px;
  padding: 3rem;
}

.history-list {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
}
</style>