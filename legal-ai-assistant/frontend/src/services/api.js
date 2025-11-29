// src/services/api.js
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and haven't retried yet, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (refreshToken) {
          const response = await axios.post(
            `${API_BASE_URL}/auth/token/refresh`,
            { refresh: refreshToken }
          )

          const { access } = response.data
          localStorage.setItem('access_token', access)

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  register(username, email, password) {
    return api.post('/auth/register', { username, email, password })
  },
  
  login(username, password) {
    return api.post('/auth/login', { username, password })
  },
  
  logout(refreshToken) {
    return api.post('/auth/logout', { refresh: refreshToken })
  },
  
  getProfile() {
    return api.get('/auth/profile')
  },
  
  updateSettings(settings) {
    return api.put('/auth/settings', settings)
  },
  
  updateOrgProfile(profile) {
    return api.put('/auth/org-profile', profile)
  },
}

// Chat API
export const chatAPI = {
  sendMessage(data) {
    console.log('Sending chat request:', data)
    return api.post('/chat', data).then(response => {
      console.log('Chat response received:', response)
      return response
    }).catch(error => {
      console.error('Chat request failed:', error)
      throw error
    })
  },
}

// Document API
export const documentAPI = {
  list(params) {
    return api.get('/documents', { params })
  },
  
  get(id) {
    return api.get(`/documents/${id}`)
  },
  
  upload(formData) {
    return api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  delete(id) {
    return api.delete(`/documents/${id}/delete`)
  },
  
  getContent(id) {
    return api.get(`/documents/${id}/content`)
  },
}

// History API
export const historyAPI = {
  list(params) {
    return api.get('/history', { params })
  },
  
  get(id) {
    return api.get(`/history/${id}`)
  },
  
  delete(id) {
    return api.delete(`/history/${id}/delete`)
  },
  
  export(filters) {
    return api.post('/history/export', filters)
  },
}

// RAG API
export const ragAPI = {
  ingest(documentId, reindex = false) {
    return api.post('/ingest', { document_id: documentId, reindex })
  },
  
  search(query, k = 10, filters = {}) {
    return api.post('/search', { query, k, filters })
  },
  
  stats() {
    return api.get('/rag/stats')
  },
}

// Health API
export const healthAPI = {
  check() {
    return api.get('/health/check')
  },
}


export default api