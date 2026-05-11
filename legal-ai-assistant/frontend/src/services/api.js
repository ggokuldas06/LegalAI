// src/services/api.js
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach auth token on every request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error),
)

// Auto-refresh token on 401
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        const refresh = localStorage.getItem('refresh_token')
        if (refresh) {
          const res = await axios.post(`${API_BASE_URL}/auth/token/refresh`, { refresh })
          localStorage.setItem('access_token', res.data.access)
          original.headers.Authorization = `Bearer ${res.data.access}`
          return api(original)
        }
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

// Auth API
export const authAPI = {
  register: (username, email, password) =>
    api.post('/auth/register', { username, email, password }),
  login: (username, password) =>
    api.post('/auth/login', { username, password }),
  logout: (refreshToken) =>
    api.post('/auth/logout', { refresh: refreshToken }),
  getProfile: () => api.get('/auth/profile'),
  updateSettings: (settings) => api.put('/auth/settings', settings),
  updateOrgProfile: (profile) => api.put('/auth/org-profile', profile),
}

// Chat API
export const chatAPI = {
  /** Non-streaming fallback */
  sendMessage(data) {
    return api.post('/chat', { ...data, stream: false })
  },

  /**
   * Streaming chat via Server-Sent Events.
   * @param {Object} payload  - request body (mode, message, …)
   * @param {Object} handlers - { onToken, onDone, onError }
   */
  async sendMessageStream(payload, { onToken, onDone, onError } = {}) {
    const token = localStorage.getItem('access_token')
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    }

    let response
    try {
      response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ ...payload, stream: true }),
      })
    } catch (err) {
      onError?.(err.message || 'Network error')
      return
    }

    if (!response.ok) {
      let msg = `HTTP ${response.status}`
      try {
        const body = await response.json()
        msg = body.error || msg
      } catch { /* ignore */ }
      onError?.(msg)
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() // keep incomplete last line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const json = line.slice(6).trim()
        if (!json) continue

        try {
          const chunk = JSON.parse(json)
          if (chunk.type === 'token') {
            onToken?.(chunk.token || '')
          } else if (chunk.type === 'done') {
            onDone?.(chunk)
          } else if (chunk.type === 'error') {
            onError?.(chunk.error || 'Unknown streaming error')
          }
        } catch { /* skip malformed line */ }
      }
    }
  },
}

// Document API
export const documentAPI = {
  list: (params) => api.get('/documents', { params }),
  get: (id) => api.get(`/documents/${id}`),
  upload: (formData) =>
    api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  delete: (id) => api.delete(`/documents/${id}/delete`),
  getContent: (id) => api.get(`/documents/${id}/content`),
}

// History API
export const historyAPI = {
  list: (params) => api.get('/history', { params }),
  get: (id) => api.get(`/history/${id}`),
  delete: (id) => api.delete(`/history/${id}/delete`),
  export: (filters) => api.post('/history/export', filters),
}

// RAG API
export const ragAPI = {
  ingest: (documentId, reindex = false) =>
    api.post('/ingest', { document_id: documentId, reindex }),
  search: (query, k = 10, filters = {}) =>
    api.post('/search', { query, k, filters }),
  stats: () => api.get('/rag/stats'),
}

// Health API
export const healthAPI = {
  check: () => api.get('/health/check'),
}

export default api
