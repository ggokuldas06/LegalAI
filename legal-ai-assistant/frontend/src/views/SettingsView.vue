<!-- src/views/SettingsView.vue -->
<template>
  <div class="settings-view container py-4">
    <h2 class="mb-4">
      <i class="bi bi-gear me-2"></i>
      Settings
    </h2>
    
    <AlertMessage
      :show="!!alert.message"
      :type="alert.type"
      :message="alert.message"
      @close="alert.message = ''"
    />
    
    <div class="row">
      <!-- User Information -->
      <div class="col-md-6 mb-4">
        <div class="card">
          <div class="card-header bg-primary text-white">
            <h5 class="mb-0">
              <i class="bi bi-person me-2"></i>
              User Information
            </h5>
          </div>
          <div class="card-body">
            <div class="mb-3">
              <label class="form-label fw-bold">Username</label>
              <input
                type="text"
                class="form-control"
                :value="authStore.username"
                disabled
              >
            </div>
            <div class="mb-3">
              <label class="form-label fw-bold">Email</label>
              <input
                type="email"
                class="form-control"
                :value="authStore.userEmail"
                disabled
              >
            </div>
            <div>
              <label class="form-label fw-bold">Member Since</label>
              <input
                type="text"
                class="form-control"
                :value="formatDate(authStore.user?.date_joined)"
                disabled
              >
            </div>
          </div>
        </div>
      </div>
      
      <!-- Inference Settings -->
      <div class="col-md-6 mb-4">
        <div class="card">
          <div class="card-header bg-success text-white">
            <h5 class="mb-0">
              <i class="bi bi-sliders me-2"></i>
              Inference Settings
            </h5>
          </div>
          <div class="card-body">
            <form @submit.prevent="saveInferenceSettings">
              <div class="mb-4">
                <label class="form-label fw-bold">
                  Temperature: {{ inferenceSettings.temperature }}
                </label>
                <input
                  v-model.number="inferenceSettings.temperature"
                  type="range"
                  class="form-range"
                  min="0"
                  max="2"
                  step="0.1"
                >
                <div class="d-flex justify-content-between">
                  <small class="text-muted">More Focused (0.0)</small>
                  <small class="text-muted">More Creative (2.0)</small>
                </div>
                <small class="text-muted d-block mt-1">
                  Controls randomness in responses
                </small>
              </div>
              
              <div class="mb-4">
                <label class="form-label fw-bold">
                  Max Tokens: {{ inferenceSettings.max_tokens }}
                </label>
                <input
                  v-model.number="inferenceSettings.max_tokens"
                  type="range"
                  class="form-range"
                  min="50"
                  max="2048"
                  step="50"
                >
                <div class="d-flex justify-content-between">
                  <small class="text-muted">Shorter (50)</small>
                  <small class="text-muted">Longer (2048)</small>
                </div>
                <small class="text-muted d-block mt-1">
                  Maximum length of generated responses
                </small>
              </div>
              
              <div class="mb-4">
                <label class="form-label fw-bold">
                  Top P: {{ inferenceSettings.top_p }}
                </label>
                <input
                  v-model.number="inferenceSettings.top_p"
                  type="range"
                  class="form-range"
                  min="0"
                  max="1"
                  step="0.05"
                >
                <small class="text-muted">
                  Nucleus sampling threshold
                </small>
              </div>
              
              <div class="mb-4">
                <label class="form-label fw-bold">
                  Top K: {{ inferenceSettings.top_k }}
                </label>
                <input
                  v-model.number="inferenceSettings.top_k"
                  type="range"
                  class="form-range"
                  min="1"
                  max="100"
                  step="1"
                >
                <small class="text-muted">
                  Number of top tokens to consider
                </small>
              </div>
              
              <button
                type="submit"
                class="btn btn-success w-100"
                :disabled="isSaving"
              >
                <span v-if="isSaving" class="spinner-border spinner-border-sm me-2"></span>
                {{ isSaving ? 'Saving...' : 'Save Inference Settings' }}
              </button>
            </form>
          </div>
        </div>
      </div>
      
      <!-- Mode C Default Filters -->
      <div class="col-md-6 mb-4">
        <div class="card">
          <div class="card-header bg-info text-white">
            <h5 class="mb-0">
              <i class="bi bi-funnel me-2"></i>
              Default Filters (Mode C)
            </h5>
          </div>
          <div class="card-body">
            <form @submit.prevent="saveInferenceSettings">
              <div class="mb-3">
                <label class="form-label fw-bold">Default Jurisdiction</label>
                <select v-model="inferenceSettings.default_jurisdiction" class="form-select">
                  <option value="">None</option>
                  <option value="US">United States</option>
                  <option value="US-CA">US - California</option>
                  <option value="US-NY">US - New York</option>
                  <option value="EU">European Union</option>
                  <option value="UK">United Kingdom</option>
                </select>
              </div>
              
              <div class="mb-3">
                <label class="form-label fw-bold">Default Year Range</label>
                <div class="row g-2">
                  <div class="col-6">
                    <input
                      v-model.number="inferenceSettings.default_year_from"
                      type="number"
                      class="form-control"
                      placeholder="From"
                      min="1900"
                      :max="currentYear"
                    >
                  </div>
                  <div class="col-6">
                    <input
                      v-model.number="inferenceSettings.default_year_to"
                      type="number"
                      class="form-control"
                      placeholder="To"
                      min="1900"
                      :max="currentYear"
                    >
                  </div>
                </div>
              </div>
              
              <button
                type="submit"
                class="btn btn-info w-100 text-white"
                :disabled="isSaving"
              >
                <span v-if="isSaving" class="spinner-border spinner-border-sm me-2"></span>
                {{ isSaving ? 'Saving...' : 'Save Filter Defaults' }}
              </button>
            </form>
          </div>
        </div>
      </div>
      
      <!-- Organization Profile -->
      <div class="col-md-6 mb-4">
        <div class="card">
          <div class="card-header bg-warning text-dark">
            <h5 class="mb-0">
              <i class="bi bi-building me-2"></i>
              Organization Profile
            </h5>
          </div>
          <div class="card-body">
            <form @submit.prevent="saveOrgProfile">
              <div class="mb-3">
                <label class="form-label fw-bold">Preferred Jurisdictions</label>
                <input
                  v-model="jurisdictionsInput"
                  type="text"
                  class="form-control"
                  placeholder="e.g., US, EU, UK (comma-separated)"
                >
                <small class="text-muted">
                  Your frequently used jurisdictions
                </small>
              </div>
              
              <div class="mb-3">
                <label class="form-label fw-bold">Common Clause Types</label>
                <input
                  v-model="clauseSetInput"
                  type="text"
                  class="form-control"
                  placeholder="e.g., Termination, Indemnity (comma-separated)"
                >
                <small class="text-muted">
                  Clause types you work with most
                </small>
              </div>
              
              <button
                type="submit"
                class="btn btn-warning w-100"
                :disabled="isSavingOrg"
              >
                <span v-if="isSavingOrg" class="spinner-border spinner-border-sm me-2"></span>
                {{ isSavingOrg ? 'Saving...' : 'Save Organization Profile' }}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Danger Zone -->
    <div class="card border-danger mb-4">
      <div class="card-header bg-danger text-white">
        <h5 class="mb-0">
          <i class="bi bi-exclamation-triangle me-2"></i>
          Danger Zone
        </h5>
      </div>
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <strong>Logout</strong>
            <p class="text-muted mb-0">Sign out of your account</p>
          </div>
          <button class="btn btn-outline-danger" @click="handleLogout">
            <i class="bi bi-box-arrow-right me-2"></i>
            Logout
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AlertMessage from '@/components/common/AlertMessage.vue'

const router = useRouter()
const authStore = useAuthStore()

const isSaving = ref(false)
const isSavingOrg = ref(false)
const alert = ref({ type: 'info', message: '' })
const currentYear = new Date().getFullYear()

const inferenceSettings = ref({
  temperature: 0.7,
  max_tokens: 256,
  top_p: 0.9,
  top_k: 50,
  default_jurisdiction: '',
  default_year_from: null,
  default_year_to: null,
})

const jurisdictionsInput = ref('')
const clauseSetInput = ref('')

const loadSettings = () => {
  if (authStore.settings) {
    inferenceSettings.value = { ...authStore.settings }
  }
  
  if (authStore.orgProfile) {
    jurisdictionsInput.value = authStore.orgProfile.jurisdictions?.join(', ') || ''
    clauseSetInput.value = authStore.orgProfile.clause_set?.join(', ') || ''
  }
}

const saveInferenceSettings = async () => {
  isSaving.value = true
  alert.value = { type: 'info', message: '' }
  
  const result = await authStore.updateSettings(inferenceSettings.value)
  
  if (result.success) {
    alert.value = { type: 'success', message: 'Settings saved successfully!' }
  } else {
    alert.value = { type: 'danger', message: result.error || 'Failed to save settings' }
  }
  
  isSaving.value = false
}

const saveOrgProfile = async () => {
  isSavingOrg.value = true
  alert.value = { type: 'info', message: '' }
  
  const profile = {
    jurisdictions: jurisdictionsInput.value
      .split(',')
      .map(j => j.trim())
      .filter(j => j),
    clause_set: clauseSetInput.value
      .split(',')
      .map(c => c.trim())
      .filter(c => c),
  }
  
  const result = await authStore.updateOrgProfile(profile)
  
  if (result.success) {
    alert.value = { type: 'success', message: 'Organization profile saved successfully!' }
  } else {
    alert.value = { type: 'danger', message: result.error || 'Failed to save profile' }
  }
  
  isSavingOrg.value = false
}

const handleLogout = async () => {
  if (confirm('Are you sure you want to logout?')) {
    await authStore.logout()
    router.push('/login')
  }
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString()
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-view {
  min-height: calc(100vh - 56px);
  background: #f8f9fa;
}

.card {
  border-radius: 12px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  border-radius: 12px 12px 0 0 !important;
}

.form-range {
  cursor: pointer;
}
</style>