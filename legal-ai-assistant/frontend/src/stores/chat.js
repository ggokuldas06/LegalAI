// src/stores/chat.js
import { defineStore } from 'pinia'
import { chatAPI } from '@/services/api'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    currentMode: 'A',
    selectedDocument: null,
    selectedCase: null,
    isLoading: false,
    isStreaming: false,
    error: null,
    filters: {
      jurisdiction: '',
      year_from: null,
      year_to: null,
      include: [],
      exclude: [],
    },
  }),

  getters: {
    modeLabel: (state) => {
      const labels = {
        A: 'Summarizer',
        B: 'Clause Classifier',
        C: 'Case-Law IRAC',
        D: 'Case Agentic Q&A',
      }
      return labels[state.currentMode] || 'Unknown'
    },
  },

  actions: {
    setMode(mode) {
      this.currentMode = mode
      this.messages = []
      this.error = null
    },

    setDocument(document) {
      this.selectedDocument = document
    },

    setCase(c) {
      this.selectedCase = c
    },

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    },

    async sendMessage(message, settings = {}) {
      this.isLoading = true
      this.isStreaming = false
      this.error = null

      this.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date(),
      })

      const payload = {
        mode: this.currentMode,
        message,
        stream: true,
      }

      if (this.currentMode === 'A' || this.currentMode === 'B') {
        if (!this.selectedDocument) throw new Error('Please select a document first')
        payload.doc_id = this.selectedDocument.id
      }

      if (this.currentMode === 'C') {
        payload.filters = this.filters
        if (this.selectedDocument) {
          payload.doc_id = this.selectedDocument.id
        }
      }

      if (this.currentMode === 'D') {
        if (!this.selectedCase) throw new Error('Please select a case first')
        payload.case_id = this.selectedCase.id
      }

      // Add placeholder assistant message for streaming
      const assistantMsgIndex = this.messages.length
      this.messages.push({
        role: 'assistant',
        content: '',
        streaming: true,
        timestamp: new Date(),
      })

      try {
        await chatAPI.sendMessageStream(payload, {
          onStart: (startChunk) => {
            if (startChunk.agent_trace) {
              this.messages[assistantMsgIndex].agent_trace = startChunk.agent_trace
            }
          },
          onToken: (token) => {
            this.isStreaming = true
            this.messages[assistantMsgIndex].content += token
          },
          onDone: (doneChunk) => {
            this.messages[assistantMsgIndex].streaming = false
            this.messages[assistantMsgIndex].chat_log_id = doneChunk.chat_log_id
            if (doneChunk.disclaimer) {
              this.messages[assistantMsgIndex].content += doneChunk.disclaimer
            }
          },
          onError: (err) => {
            this.messages[assistantMsgIndex].role = 'error'
            this.messages[assistantMsgIndex].content = err
            this.messages[assistantMsgIndex].streaming = false
            this.error = err
          },
        })
      } catch (error) {
        this.error = error.message
        this.messages[assistantMsgIndex].role = 'error'
        this.messages[assistantMsgIndex].content = error.message
        this.messages[assistantMsgIndex].streaming = false
      } finally {
        this.isLoading = false
        this.isStreaming = false
      }
    },

    clearMessages() {
      this.messages = []
      this.error = null
    },

    removeMessage(index) {
      this.messages.splice(index, 1)
    },
  },
})
