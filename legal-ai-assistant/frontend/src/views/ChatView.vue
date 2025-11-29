<!-- src/views/ChatView.vue -->
<template>
  <div class="chat-view">
    <div class="container-fluid h-100">
      <div class="row h-100">
        <!-- Sidebar -->
        <div class="col-md-3 sidebar">
          <div class="sidebar-content">
            <h5 class="mb-3">
              <i class="bi bi-sliders me-2"></i>
              Configuration
            </h5>
            
            <!-- Mode Selector -->
            <div class="mb-4">
              <label class="form-label fw-bold">Mode</label>
              <ModeSelector v-model="chatStore.currentMode" @update:model-value="handleModeChange" />
            </div>
            
            <!-- Document Selector (for modes A & B) -->
            <div v-if="showDocumentSelector" class="mb-4">
              <DocumentSelector v-model="selectedDocument" />
            </div>
            
            <!-- Filters (for mode C) -->
            <div v-if="chatStore.currentMode === 'C'" class="mb-4">
              <FilterPanel v-model="chatStore.filters" />
            </div>
            
            <!-- Settings Quick Access -->
            <div class="mb-4">
              <label class="form-label fw-bold">Settings</label>
              <SettingsQuick />
            </div>
            
            <!-- Clear Chat -->
            <button
              class="btn btn-outline-danger w-100"
              @click="handleClearChat"
              :disabled="chatStore.messages.length === 0"
            >
              <i class="bi bi-trash me-2"></i>
              Clear Chat
            </button>
          </div>
        </div>
        
        <!-- Main Chat Area -->
        <div class="col-md-9 chat-area">
          <div class="chat-container">
            <!-- Header -->
            <div class="chat-header">
              <h4>
                <i class="bi bi-chat-dots me-2"></i>
                {{ chatStore.modeLabel }}
              </h4>
              <span class="badge bg-primary">{{ chatStore.messages.length }} messages</span>
            </div>
            
            <!-- Messages -->
            <div class="chat-messages" ref="messagesContainer">
              <div v-if="chatStore.messages.length === 0" class="empty-state">
                <i class="bi bi-chat-text display-1 text-muted"></i>
                <h5 class="mt-3">Start a Conversation</h5>
                <p class="text-muted">
                  {{ getEmptyStateMessage() }}
                </p>
              </div>
              
              <ChatMessage
                v-for="(message, index) in chatStore.messages"
                :key="index"
                :message="message"
              />
              
              <div v-if="chatStore.isLoading" class="loading-message">
                <div class="message-avatar">
                  <div class="spinner-border spinner-border-sm text-primary"></div>
                </div>
                <div class="message-content">
                  <em class="text-muted">AI is thinking...</em>
                </div>
              </div>
            </div>
            
            <!-- Input -->
            <ChatInput
              :disabled="chatStore.isLoading || !canSendMessage"
              @send="handleSendMessage"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import ModeSelector from '@/components/chat/ModeSelector.vue'
import DocumentSelector from '@/components/chat/DocumentSelector.vue'
import FilterPanel from '@/components/chat/FilterPanel.vue'
import SettingsQuick from '@/components/chat/SettingsQuick.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()
const authStore = useAuthStore()

const messagesContainer = ref(null)
const selectedDocument = ref(null)

const showDocumentSelector = computed(() => {
  return chatStore.currentMode === 'A' || chatStore.currentMode === 'B'
})

const canSendMessage = computed(() => {
  if (chatStore.currentMode === 'A' || chatStore.currentMode === 'B') {
    return !!selectedDocument.value
  }
  return true
})

const handleModeChange = () => {
  chatStore.clearMessages()
  selectedDocument.value = null
}

const handleSendMessage = async (message) => {
  // Set selected document in store
  if (selectedDocument.value) {
    chatStore.setDocument(selectedDocument.value)
  }
  
  // Get user settings
  const settings = authStore.settings || {}
  
  await chatStore.sendMessage(message, settings)
  
  // Scroll to bottom
  await nextTick()
  scrollToBottom()
}

const handleClearChat = () => {
  if (confirm('Are you sure you want to clear this chat?')) {
    chatStore.clearMessages()
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const getEmptyStateMessage = () => {
  const messages = {
    A: 'Select a document and ask for a summary',
    B: 'Select a document to extract and classify clauses',
    C: 'Ask legal questions and get IRAC-structured answers',
  }
  return messages[chatStore.currentMode] || 'Send a message to start'
}

// Watch for new messages and scroll
watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.chat-view {
  height: calc(100vh - 56px); /* Account for navbar */
  overflow: hidden;
}

.container-fluid {
  height: 100%;
  padding: 0;
}

.row {
  height: 100%;
  margin: 0;
}

/* Sidebar */
.sidebar {
  background: #f8f9fa;
  border-right: 1px solid #dee2e6;
  height: 100%;
  overflow-y: auto;
  padding: 0;
}

.sidebar-content {
  padding: 1.5rem;
}

/* Chat Area */
.chat-area {
  height: 100%;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 1rem 1.5rem;
  background: white;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
  background: #fff;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.loading-message {
  display: flex;
  gap: 1rem;
  align-items: center;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 12px;
}

.loading-message .message-avatar {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    display: none; /* Hide sidebar on mobile, add toggle button if needed */
  }
  
  .chat-area {
    max-width: 100%;
  }
}
</style>