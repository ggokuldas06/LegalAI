// src/stores/documents.js
import { defineStore } from 'pinia'
import { documentAPI, ragAPI } from '@/services/api'

export const useDocumentStore = defineStore('documents', {
  state: () => ({
    documents: [],
    total: 0,
    isLoading: false,
    uploadProgress: 0,
    currentDocument: null,
  }),

  getters: {
    getDocumentById: (state) => (id) => {
      return state.documents.find((doc) => doc.id === id)
    },
  },

  actions: {
    async fetchDocuments(params = {}) {
      this.isLoading = true
      try {
        const response = await documentAPI.list(params)
        const data = response.data.data

        this.documents = data.results
        this.total = data.total

        return { success: true }
      } catch (error) {
        console.error('Fetch documents error:', error)
        return { success: false, error: error.message }
      } finally {
        this.isLoading = false
      }
    },

    async uploadDocument(file, metadata) {
      this.isLoading = true
      this.uploadProgress = 0

      try {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('doctype', metadata.doctype)
        formData.append('title', metadata.title)
        if (metadata.jurisdiction) formData.append('jurisdiction', metadata.jurisdiction)
        if (metadata.date) formData.append('date', metadata.date)
        if (metadata.source) formData.append('source', metadata.source)

        const response = await documentAPI.upload(formData)
        const document = response.data.data

        // Add to list
        this.documents.unshift(document)
        this.total++

        return { success: true, document }
      } catch (error) {
        console.error('Upload document error:', error)
        return {
          success: false,
          error: error.response?.data?.error || error.message,
        }
      } finally {
        this.isLoading = false
        this.uploadProgress = 0
      }
    },

    async deleteDocument(id) {
      try {
        await documentAPI.delete(id)

        // Remove from list
        const index = this.documents.findIndex((doc) => doc.id === id)
        if (index !== -1) {
          this.documents.splice(index, 1)
          this.total--
        }

        return { success: true }
      } catch (error) {
        console.error('Delete document error:', error)
        return { success: false, error: error.message }
      }
    },

    async ingestDocument(id, reindex = false) {
      try {
        const response = await ragAPI.ingest(id, reindex)
        return { success: true, data: response.data.data }
      } catch (error) {
        console.error('Ingest document error:', error)
        return {
          success: false,
          error: error.response?.data?.error || error.message,
        }
      }
    },

    async getDocumentContent(id) {
      try {
        const response = await documentAPI.getContent(id)
        return { success: true, data: response.data.data }
      } catch (error) {
        console.error('Get document content error:', error)
        return { success: false, error: error.message }
      }
    },

    setCurrentDocument(document) {
      this.currentDocument = document
    },
  },
})