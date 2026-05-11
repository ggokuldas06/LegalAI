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

            <div class="mb-3">
              <label class="form-label fw-bold">Mode</label>
              <ModeSelector v-model="chatStore.currentMode" @update:model-value="handleModeChange" />
            </div>

            <div class="mb-3">
              <DocumentSelector
                v-model="selectedDocument"
                :mode="chatStore.currentMode"
                :is-required="chatStore.currentMode !== 'C'"
              />
            </div>

            <div v-if="chatStore.currentMode === 'C'" class="mb-3">
              <FilterPanel v-model="chatStore.filters" />
            </div>

            <button
              class="btn btn-outline-danger w-100 mt-1"
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
              <div>
                <h4 class="mb-0">
                  <i class="bi bi-chat-dots me-2"></i>
                  {{ chatStore.modeLabel }}
                </h4>
                <small v-if="chatStore.currentMode === 'C' && selectedDocument" class="text-muted">
                  Searching within: {{ selectedDocument.title }}
                </small>
                <small v-else-if="chatStore.currentMode === 'C'" class="text-muted">
                  Searching all indexed documents
                </small>
              </div>
              <span class="badge bg-primary">{{ chatStore.messages.length }} messages</span>
            </div>

            <!-- Messages -->
            <div class="chat-messages" ref="messagesContainer">
              <div v-if="chatStore.messages.length === 0" class="empty-state">
                <i class="bi bi-chat-text display-1 text-muted"></i>
                <h5 class="mt-3">{{ emptyStateTitle }}</h5>
                <p class="text-muted">{{ emptyStateMessage }}</p>
              </div>

              <ChatMessage
                v-for="(message, index) in chatStore.messages"
                :key="index"
                :message="message"
              />

              <div v-if="chatStore.isLoading && !chatStore.isStreaming" class="loading-message">
                <div class="message-avatar">
                  <div class="spinner-border spinner-border-sm text-primary"></div>
                </div>
                <div class="message-content">
                  <em class="text-muted">Connecting to model…</em>
                </div>
              </div>
            </div>

            <!-- Mode A / B — single action button, no text input -->
            <div v-if="chatStore.currentMode === 'A' || chatStore.currentMode === 'B'" class="action-bar">
              <div v-if="!selectedDocument" class="no-doc-hint">
                <i class="bi bi-arrow-left me-1"></i>
                Select a document from the sidebar first
              </div>
              <button
                v-else
                class="btn btn-primary btn-lg w-100"
                :disabled="chatStore.isLoading"
                @click="handleActionButton"
              >
                <span v-if="chatStore.isLoading">
                  <span class="spinner-border spinner-border-sm me-2"></span>
                  {{ chatStore.currentMode === 'A' ? 'Summarising…' : 'Extracting clauses…' }}
                </span>
                <span v-else>
                  <i :class="chatStore.currentMode === 'A' ? 'bi bi-file-earmark-text' : 'bi bi-list-check'" class="me-2"></i>
                  {{ chatStore.currentMode === 'A' ? 'Summarise Document' : 'Extract & Classify Clauses' }}
                </span>
              </button>
            </div>

            <!-- Mode C — normal text input -->
            <ChatInput
              v-else
              :disabled="chatStore.isLoading"
              placeholder="Ask a legal question…"
              @send="handleSendMessage"
            />

          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import ModeSelector from '@/components/chat/ModeSelector.vue'
import DocumentSelector from '@/components/chat/DocumentSelector.vue'
import FilterPanel from '@/components/chat/FilterPanel.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()
const messagesContainer = ref(null)
const selectedDocument = ref(null)

const emptyStateTitle = computed(() => {
  if (chatStore.currentMode === 'A') return 'Document Summariser'
  if (chatStore.currentMode === 'B') return 'Clause Classifier'
  return 'Legal Research Assistant'
})

const emptyStateMessage = computed(() => {
  if (chatStore.currentMode === 'A') return 'Select a document in the sidebar, then click Summarise Document.'
  if (chatStore.currentMode === 'B') return 'Select a document in the sidebar, then click Extract & Classify Clauses.'
  return 'Ask any legal question. Optionally filter to a specific indexed document.'
})

const handleModeChange = () => {
  chatStore.clearMessages()
  selectedDocument.value = null
  chatStore.setDocument(null)
}

// Modes A / B — fire a fixed trigger message; backend uses document text, not the message
const handleActionButton = async () => {
  chatStore.setDocument(selectedDocument.value)
  const trigger = chatStore.currentMode === 'A'
    ? `Summarise document: ${selectedDocument.value.title}`
    : `Extract and classify all clauses from: ${selectedDocument.value.title}`
  await chatStore.sendMessage(trigger)
  await nextTick()
  scrollToBottom()
}

// Mode C — user types a question
const handleSendMessage = async (message) => {
  chatStore.setDocument(selectedDocument.value)
  await chatStore.sendMessage(message)
  await nextTick()
  scrollToBottom()
}

const handleClearChat = () => {
  if (confirm('Clear this chat?')) chatStore.clearMessages()
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

watch(() => chatStore.messages.length, async () => {
  await nextTick()
  scrollToBottom()
})

watch(
  () => chatStore.messages[chatStore.messages.length - 1]?.content?.length,
  async () => { await nextTick(); scrollToBottom() }
)
</script>

<style scoped>
.chat-view {
  height: calc(100vh - 56px);
  overflow: hidden;
}

.container-fluid { height: 100%; padding: 0; }
.row { height: 100%; margin: 0; }

.sidebar {
  background: #f8f9fa;
  border-right: 1px solid #dee2e6;
  height: 100%;
  overflow-y: auto;
  padding: 0;
}

.sidebar-content { padding: 1.25rem; }

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
  padding: 0.875rem 1.5rem;
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

/* Action bar for modes A / B */
.action-bar {
  background: white;
  border-top: 1px solid #dee2e6;
  padding: 1rem 1.5rem;
}

.no-doc-hint {
  text-align: center;
  color: #6c757d;
  padding: 0.5rem;
  font-size: 0.9rem;
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

@media (max-width: 768px) {
  .sidebar { display: none; }
  .chat-area { max-width: 100%; }
}
</style>
