// src/stores/auth.js
import { defineStore } from 'pinia'
import { authAPI } from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
    isAuthenticated: !!localStorage.getItem('access_token'),
    settings: null,
    orgProfile: null,
  }),

  getters: {
    username: (state) => state.user?.username,
    userEmail: (state) => state.user?.email,
  },

  actions: {
    async login(username, password) {
      try {
        const response = await authAPI.login(username, password)
        const { user, tokens } = response.data.data

        this.user = user
        this.accessToken = tokens.access
        this.refreshToken = tokens.refresh
        this.isAuthenticated = true

        localStorage.setItem('access_token', tokens.access)
        localStorage.setItem('refresh_token', tokens.refresh)

        // Fetch full profile
        await this.fetchProfile()

        return { success: true }
      } catch (error) {
        console.error('Login error:', error)
        return {
          success: false,
          error: error.response?.data?.error || 'Login failed',
        }
      }
    },

    async register(username, email, password) {
      try {
        const response = await authAPI.register(username, email, password)
        const { user, tokens } = response.data.data

        this.user = user
        this.accessToken = tokens.access
        this.refreshToken = tokens.refresh
        this.isAuthenticated = true

        localStorage.setItem('access_token', tokens.access)
        localStorage.setItem('refresh_token', tokens.refresh)

        return { success: true }
      } catch (error) {
        console.error('Registration error:', error)
        return {
          success: false,
          error: error.response?.data?.error || 'Registration failed',
        }
      }
    },

    async logout() {
      try {
        if (this.refreshToken) {
          await authAPI.logout(this.refreshToken)
        }
      } catch (error) {
        console.error('Logout error:', error)
      } finally {
        this.user = null
        this.accessToken = null
        this.refreshToken = null
        this.isAuthenticated = false
        this.settings = null
        this.orgProfile = null

        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      }
    },

    async fetchProfile() {
      try {
        const response = await authAPI.getProfile()
        const data = response.data.data

        this.user = {
          id: data.id,
          username: data.username,
          email: data.email,
          date_joined: data.date_joined,
        }
        this.settings = data.settings
        this.orgProfile = data.org_profile

        return { success: true }
      } catch (error) {
        console.error('Fetch profile error:', error)
        return { success: false, error: error.message }
      }
    },

    async updateSettings(settings) {
      try {
        const response = await authAPI.updateSettings(settings)
        this.settings = response.data.data
        return { success: true }
      } catch (error) {
        console.error('Update settings error:', error)
        return {
          success: false,
          error: error.response?.data?.error || 'Update failed',
        }
      }
    },

    async updateOrgProfile(profile) {
      try {
        const response = await authAPI.updateOrgProfile(profile)
        this.orgProfile = response.data.data
        return { success: true }
      } catch (error) {
        console.error('Update org profile error:', error)
        return { success: false, error: error.message }
      }
    },
  },
})