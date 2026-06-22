// src/stores/cases.js
import { defineStore } from 'pinia'
import { casesAPI } from '@/services/api'

export const useCasesStore = defineStore('cases', {
  state: () => ({
    cases: [],
    currentCase: null,
    isLoading: false,
    error: null,
  }),

  actions: {
    async fetchCases() {
      this.isLoading = true
      this.error = null
      try {
        const res = await casesAPI.list()
        this.cases = res.data.data
      } catch (e) {
        this.error = e.response?.data?.error || e.message
      } finally {
        this.isLoading = false
      }
    },

    async fetchCase(id) {
      this.isLoading = true
      this.error = null
      try {
        const res = await casesAPI.get(id)
        this.currentCase = res.data.data
        return this.currentCase
      } catch (e) {
        this.error = e.response?.data?.error || e.message
        return null
      } finally {
        this.isLoading = false
      }
    },

    async createCase(title, description = '') {
      const res = await casesAPI.create({ title, description })
      this.cases.unshift(res.data.data)
      return res.data.data
    },

    async updateCase(id, data) {
      const res = await casesAPI.update(id, data)
      const updated = res.data.data
      const idx = this.cases.findIndex((c) => c.id === id)
      if (idx !== -1) this.cases[idx] = { ...this.cases[idx], ...updated }
      if (this.currentCase?.id === id) this.currentCase = updated
      return updated
    },

    async deleteCase(id) {
      await casesAPI.delete(id)
      this.cases = this.cases.filter((c) => c.id !== id)
      if (this.currentCase?.id === id) this.currentCase = null
    },

    async addDocuments(caseId, docIds, role = 'other') {
      await casesAPI.addDocuments(caseId, docIds, role)
      await this.fetchCase(caseId)
    },

    async removeDocument(caseId, docId) {
      await casesAPI.removeDocument(caseId, docId)
      if (this.currentCase?.id === caseId) {
        this.currentCase.case_documents = this.currentCase.case_documents.filter(
          (cd) => cd.document.id !== docId
        )
        this.currentCase.document_count = Math.max(0, (this.currentCase.document_count || 1) - 1)
      }
    },
  },
})
