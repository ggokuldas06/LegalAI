<!-- src/components/chat/SettingsQuick.vue -->
<template>
  <div class="settings-quick">
    <div class="setting-item mb-3">
      <label class="form-label small">
        Temperature: {{ settings.temperature }}
      </label>
      <input
        v-model.number="settings.temperature"
        type="range"
        class="form-range"
        min="0"
        max="2"
        step="0.1"
        @change="saveSettings"
      >
      <div class="d-flex justify-content-between">
        <small class="text-muted">Focused</small>
        <small class="text-muted">Creative</small>
      </div>
    </div>
    
    <div class="setting-item mb-3">
      <label class="form-label small">
        Max Tokens: {{ settings.max_tokens }}
      </label>
      <input
        v-model.number="settings.max_tokens"
        type="range"
        class="form-range"
        min="50"
        max="2048"
        step="50"
        @change="saveSettings"
      >
      <div class="d-flex justify-content-between">
        <small class="text-muted">Short</small>
        <small class="text-muted">Long</small>
      </div>
    </div>
    
    <router-link to="/settings" class="btn btn-sm btn-outline-primary w-100">
      <i class="bi bi-gear me-1"></i>
      More Settings
    </router-link>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const settings = ref({
  temperature: 0.7,
  max_tokens: 256,
})

const loadSettings = () => {
  if (authStore.settings) {
    settings.value = {
      temperature: authStore.settings.temperature || 0.7,
      max_tokens: authStore.settings.max_tokens || 256,
    }
  }
}

const saveSettings = async () => {
  await authStore.updateSettings(settings.value)
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-quick {
  padding: 1rem;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 8px;
}

.setting-item {
  margin-bottom: 1rem;
}

.form-range {
  cursor: pointer;
}
</style>