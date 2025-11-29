<!-- src/components/chat/ChatInput.vue -->
<template>
  <div class="chat-input-container">
    <div class="input-group">
      <textarea
        v-model="message"
        class="form-control"
        placeholder="Type your message..."
        rows="3"
        :disabled="disabled"
        @keydown.enter.exact="handleSend"
        @keydown.enter.shift.exact.prevent="message += '\n'"
      ></textarea>
      
      <button
        class="btn btn-primary"
        :disabled="!message.trim() || disabled"
        @click="handleSend"
      >
        <span v-if="disabled" class="spinner-border spinner-border-sm me-2"></span>
        <i v-else class="bi bi-send"></i>
        {{ disabled ? 'Sending...' : 'Send' }}
      </button>
    </div>
    
    <div class="input-footer">
      <small class="text-muted">
        Press Enter to send, Shift+Enter for new line
      </small>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['send'])

const message = ref('')

const handleSend = () => {
  if (message.value.trim()) {
    emit('send', message.value)
    message.value = ''
  }
}
</script>

<style scoped>
.chat-input-container {
  background: white;
  border-top: 1px solid #dee2e6;
  padding: 1rem;
}

.input-group {
  display: flex;
  gap: 0.5rem;
}

.form-control {
  border-radius: 8px;
  resize: none;
}

.btn-primary {
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  white-space: nowrap;
}

.input-footer {
  margin-top: 0.5rem;
  text-align: right;
}
</style>