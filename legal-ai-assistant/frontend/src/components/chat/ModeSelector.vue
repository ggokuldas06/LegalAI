<!-- src/components/chat/ModeSelector.vue -->
<template>
  <div class="mode-selector">
    <div class="btn-group w-100" role="group">
      <button
        v-for="mode in modes"
        :key="mode.value"
        type="button"
        class="btn"
        :class="{ 'btn-primary': selectedMode === mode.value, 'btn-outline-primary': selectedMode !== mode.value }"
        @click="$emit('update:modelValue', mode.value)"
      >
        <i :class="mode.icon" class="me-2"></i>
        <div class="mode-info">
          <strong>{{ mode.label }}</strong>
          <small class="d-block text-muted">{{ mode.description }}</small>
        </div>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

defineEmits(['update:modelValue'])

const selectedMode = computed(() => props.modelValue)

const modes = [
  {
    value: 'A',
    label: 'Summarizer',
    description: 'Multi-layer document summaries',
    icon: 'bi bi-file-earmark-text',
  },
  {
    value: 'B',
    label: 'Clause Classifier',
    description: 'Extract and classify clauses',
    icon: 'bi bi-list-check',
  },
  {
    value: 'C',
    label: 'Case-Law IRAC',
    description: 'Legal research with citations',
    icon: 'bi bi-book',
  },
]
</script>

<style scoped>
.mode-selector {
  margin-bottom: 1.5rem;
}

.btn-group .btn {
  text-align: left;
  padding: 1rem;
  border-radius: 8px !important;
  margin: 0 0.25rem;
}

.mode-info {
  display: flex;
  flex-direction: column;
}

.mode-info small {
  font-size: 0.75rem;
  margin-top: 0.25rem;
}

@media (max-width: 768px) {
  .btn-group {
    flex-direction: column;
  }
  
  .btn-group .btn {
    margin: 0.25rem 0;
  }
}
</style>