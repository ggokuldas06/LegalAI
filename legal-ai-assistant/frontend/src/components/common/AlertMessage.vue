<!-- src/components/common/AlertMessage.vue -->
<template>
  <div v-if="show" :class="`alert alert-${type} alert-dismissible fade show`" role="alert">
    <i :class="iconClass" class="me-2"></i>
    {{ message }}
    <button type="button" class="btn-close" @click="$emit('close')"></button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  type: {
    type: String,
    default: 'info', // success, danger, warning, info
  },
  message: {
    type: String,
    required: true,
  },
})

defineEmits(['close'])

const iconClass = computed(() => {
  const icons = {
    success: 'bi bi-check-circle-fill',
    danger: 'bi bi-exclamation-triangle-fill',
    warning: 'bi bi-exclamation-circle-fill',
    info: 'bi bi-info-circle-fill',
  }
  return icons[props.type] || icons.info
})
</script>