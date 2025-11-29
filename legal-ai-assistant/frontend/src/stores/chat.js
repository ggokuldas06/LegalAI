// src/stores/chat.js
import { defineStore } from 'pinia'
import { chatAPI } from '@/services/api'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    currentMode: 'A', // A, B, or C
    selectedDocument: null,
    isLoading: false,
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

    setFilters(filters) {
      this.filters = { ...this.filters, ...filters }
    },

    async sendMessage(message, settings = {}) {
      this.isLoading = true
      this.error = null

      // Add user message
      this.messages.push({
        role: 'user',
        content: message,
        timestamp: new Date(),
      })

      try {
        const payload = {
          mode: this.currentMode,
          message,
          settings,
        }

        // Add document for modes A and B
        if (this.currentMode === 'A' || this.currentMode === 'B') {
          if (!this.selectedDocument) {
            throw new Error('Please select a document first')
          }
          payload.doc_id = this.selectedDocument.id
        }

        // Add filters for mode C
        if (this.currentMode === 'C') {
          payload.filters = this.filters
        }

        const response = await chatAPI.sendMessage(payload)
        const data = response.data.data

        // Add assistant message
        this.messages.push({
          role: 'assistant',
          content: data.response,
          processed: data.processed,
          citations: data.citations,
          tokens_in: data.tokens_in,
          tokens_out: data.tokens_out,
          latency_ms: data.latency_ms,
          chat_log_id: data.chat_log_id,
          timestamp: new Date(),
        })

        return { success: true, data }
      } catch (error) {
        console.error('Send message error:', error)
        this.error = error.response?.data?.error || error.message

        // Add error message
        this.messages.push({
          role: 'error',
          content: this.error,
          timestamp: new Date(),
        })

        return { success: false, error: this.error }
      } finally {
        this.isLoading = false
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