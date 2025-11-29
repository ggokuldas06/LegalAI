// src/stores/history.js
import { defineStore } from 'pinia'
import { historyAPI } from '@/services/api'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    history: [],
    total: 0,
    isLoading: false,
    currentChat: null,
  }),

  actions: {
    async fetchHistory(params = {}) {
      this.isLoading = true
      try {
        const response = await historyAPI.list(params)
        const data = response.data.data

        this.history = data.results
        this.total = data.total

        return { success: true }
      } catch (error) {
        console.error('Fetch history error:', error)
        return { success: false, error: error.message }
      } finally {
        this.isLoading = false
      }
    },

    async getChat(id) {
      try {
        const response = await historyAPI.get(id)
        this.currentChat = response.data.data
        return { success: true, data: this.currentChat }
      } catch (error) {
        console.error('Get chat error:', error)
        return { success: false, error: error.message }
      }
    },

    async deleteChat(id) {
      try {
        await historyAPI.delete(id)

        // Remove from list
        const index = this.history.findIndex((chat) => chat.id === id)
        if (index !== -1) {
          this.history.splice(index, 1)
          this.total--
        }

        return { success: true }
      } catch (error) {
        console.error('Delete chat error:', error)
        return { success: false, error: error.message }
      }
    },

    async exportHistory(filters = {}) {
      try {
        const response = await historyAPI.export(filters)
        return { success: true, data: response.data.data }
      } catch (error) {
        console.error('Export history error:', error)
        return { success: false, error: error.message }
      }
    },
  },
})