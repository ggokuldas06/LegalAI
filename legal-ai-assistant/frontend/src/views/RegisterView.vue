<!-- src/views/RegisterView.vue -->
<template>
  <div class="auth-container">
    <div class="auth-card card">
      <div class="card-body p-5">
        <div class="text-center mb-4">
          <i class="bi bi-scales display-4 text-primary"></i>
          <h2 class="mt-3">Create Account</h2>
          <p class="text-muted">Join Legal AI Assistant</p>
        </div>

        <AlertMessage
          :show="!!error"
          type="danger"
          :message="error"
          @close="error = ''"
        />

        <form @submit.prevent="handleRegister">
          <div class="mb-3">
            <label for="username" class="form-label">Username</label>
            <input
              id="username"
              v-model="username"
              type="text"
              class="form-control"
              placeholder="Choose a username"
              required
            >
          </div>

          <div class="mb-3">
            <label for="email" class="form-label">Email</label>
            <input
              id="email"
              v-model="email"
              type="email"
              class="form-control"
              placeholder="Enter your email"
              required
            >
          </div>

          <div class="mb-3">
            <label for="password" class="form-label">Password</label>
            <input
              id="password"
              v-model="password"
              type="password"
              class="form-control"
              placeholder="Create a password"
              required
              minlength="8"
            >
            <small class="text-muted">Minimum 8 characters</small>
          </div>

          <div class="mb-3">
            <label for="confirmPassword" class="form-label">Confirm Password</label>
            <input
              id="confirmPassword"
              v-model="confirmPassword"
              type="password"
              class="form-control"
              placeholder="Confirm your password"
              required
            >
          </div>

          <button
            type="submit"
            class="btn btn-primary w-100"
            :disabled="isLoading"
          >
            <span v-if="isLoading" class="spinner-border spinner-border-sm me-2"></span>
            {{ isLoading ? 'Creating account...' : 'Sign Up' }}
          </button>
        </form>

        <div class="text-center mt-4">
          <p class="text-muted">
            Already have an account?
            <router-link to="/login" class="text-primary">Sign in</router-link>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AlertMessage from '@/components/common/AlertMessage.vue'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const isLoading = ref(false)
const error = ref('')

const handleRegister = async () => {
  if (!username.value || !email.value || !password.value) {
    error.value = 'Please fill in all fields'
    return
  }

  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  if (password.value.length < 8) {
    error.value = 'Password must be at least 8 characters'
    return
  }

  isLoading.value = true
  error.value = ''

  const result = await authStore.register(
    username.value,
    email.value,
    password.value
  )

  if (result.success) {
    router.push('/chat')
  } else {
    error.value = result.error || 'Registration failed'
  }

  isLoading.value = false
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem;
}

.auth-card {
  max-width: 450px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  padding: 0.75rem;
  font-weight: 500;
}
</style>