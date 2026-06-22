<!-- src/components/chat/ChatMessage.vue -->
<template>
  <div class="chat-message" :class="message.role">
    <div class="message-avatar">
      <i :class="avatarIcon"></i>
    </div>

    <div class="message-content">
      <div class="message-header">
        <strong>{{ roleLabel }}</strong>
        <small class="text-muted">{{ formattedTime }}</small>
      </div>

      <div class="message-body">
        <!-- Error -->
        <div v-if="message.role === 'error'" class="alert alert-danger mb-0">
          <i class="bi bi-exclamation-triangle me-2"></i>{{ message.content }}
        </div>

        <!-- User -->
        <div v-else-if="message.role === 'user'" class="user-message">
          {{ message.content }}
        </div>

        <!-- Assistant -->
        <div v-else class="assistant-message">
          <!-- Agent trace (Mode D) -->
          <AgentTrace v-if="message.agent_trace" :trace="message.agent_trace" />

          <!-- Streaming cursor -->
          <div v-if="message.streaming" class="streaming-indicator mb-2">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <small class="text-muted ms-2">Generating…</small>
          </div>

          <!-- Rendered markdown content -->
          <div class="message-text markdown-body" v-html="renderedContent"></div>

          <!-- Citations -->
          <div
            v-if="message.citations && message.citations.length > 0"
            class="citations mt-3"
          >
            <strong class="d-block mb-2">
              <i class="bi bi-quote me-1"></i>Citations ({{ message.citations.length }})
            </strong>
            <div class="citation-chips">
              <span
                v-for="(citation, idx) in message.citations"
                :key="idx"
                class="badge bg-info text-dark me-1 mb-1"
              >{{ citation }}</span>
            </div>
          </div>

          <!-- Metadata (hidden while streaming) -->
          <div v-if="!message.streaming" class="message-metadata mt-2">
            <small class="text-muted">
              <span v-if="message.latency_ms">
                <i class="bi bi-clock me-1"></i>{{ message.latency_ms }}ms
                <span class="mx-2">•</span>
              </span>
              <span v-if="message.tokens_in">
                <i class="bi bi-arrow-down me-1"></i>{{ message.tokens_in }} in
                <span class="mx-2">•</span>
              </span>
              <span v-if="message.tokens_out">
                <i class="bi bi-arrow-up me-1"></i>{{ message.tokens_out }} out
              </span>
            </small>
          </div>

          <!-- Copy button -->
          <button
            v-if="!message.streaming"
            class="btn btn-sm btn-outline-secondary mt-2"
            @click="copyToClipboard"
          >
            <i class="bi bi-clipboard me-1"></i>Copy
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AgentTrace from './AgentTrace.vue'

const props = defineProps({
  message: { type: Object, required: true },
})

const avatarIcon = computed(() => {
  if (props.message.role === 'user') return 'bi bi-person-circle'
  if (props.message.role === 'assistant') return 'bi bi-robot'
  return 'bi bi-exclamation-triangle'
})

const roleLabel = computed(() => {
  if (props.message.role === 'user') return 'You'
  if (props.message.role === 'assistant') return 'AI Assistant'
  return 'Error'
})

const formattedTime = computed(() =>
  new Date(props.message.timestamp).toLocaleTimeString()
)

/** Lightweight markdown → HTML renderer (no external dependency). */
function renderMarkdown(text) {
  if (!text) return ''
  let html = text
    // Escape HTML to prevent XSS
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

    // Headings
    .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')

    // Bold & italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/__(.+?)__/g, '<strong>$1</strong>')
    .replace(/_(.+?)_/g, '<em>$1</em>')

    // Inline code
    .replace(/`(.+?)`/g, '<code>$1</code>')

    // Horizontal rule
    .replace(/^---+$/gm, '<hr>')

    // Unordered lists (- or *)
    .replace(/^[\*\-] (.+)$/gm, '<li>$1</li>')

    // Ordered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')

    // Wrap consecutive <li> in <ul>
    .replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)

    // Blockquotes
    .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')

    // Citations like [Case Name, Year] or [Section X]
    .replace(/\[([^\]]+)\]/g, '<cite class="citation-ref">[$1]</cite>')

    // Double line break → paragraph
    .replace(/\n\n/g, '</p><p>')

    // Single line break
    .replace(/\n/g, '<br>')

  return `<p>${html}</p>`
    .replace(/<p><\/p>/g, '')
    .replace(/<p>(<h[1-4]>)/g, '$1')
    .replace(/(<\/h[1-4]>)<\/p>/g, '$1')
    .replace(/<p>(<ul>)/g, '$1')
    .replace(/(<\/ul>)<\/p>/g, '$1')
    .replace(/<p>(<hr>)<\/p>/g, '$1')
}

const renderedContent = computed(() => renderMarkdown(props.message.content))

const copyToClipboard = () => {
  navigator.clipboard.writeText(props.message.content).catch(() => {})
}
</script>

<style scoped>
.chat-message {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
}

.chat-message.user .message-avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
}
.chat-message.assistant .message-avatar {
  background: #f0f4ff;
  color: #4a6cf7;
}
.chat-message.error .message-avatar {
  background: #dc3545;
  color: white;
}

.message-content { flex: 1; min-width: 0; }

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.4rem;
}

.message-body {
  background: #f8f9fa;
  padding: 1rem 1.25rem;
  border-radius: 12px;
  border: 1px solid #e9ecef;
}

.chat-message.user .message-body {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-color: transparent;
}

/* Streaming indicator */
.streaming-indicator { display: flex; align-items: center; }
.typing-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4a6cf7;
  margin: 0 2px;
  animation: bounce 1.2s infinite;
}
.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30%           { transform: translateY(-6px); }
}

/* Markdown body */
.markdown-body { line-height: 1.65; }
.markdown-body :deep(h1), .markdown-body :deep(h2) {
  font-size: 1.1rem; font-weight: 700; margin: 0.75rem 0 0.4rem;
  border-bottom: 1px solid #dee2e6; padding-bottom: 0.2rem;
}
.markdown-body :deep(h3), .markdown-body :deep(h4) {
  font-size: 1rem; font-weight: 600; margin: 0.6rem 0 0.3rem;
}
.markdown-body :deep(ul) {
  padding-left: 1.4rem; margin: 0.4rem 0;
}
.markdown-body :deep(li) { margin-bottom: 0.2rem; }
.markdown-body :deep(code) {
  background: #e9ecef; padding: 0.1em 0.4em;
  border-radius: 4px; font-size: 0.88em;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid #4a6cf7; padding-left: 0.75rem;
  color: #6c757d; margin: 0.5rem 0;
}
.markdown-body :deep(hr) { border-color: #dee2e6; margin: 0.75rem 0; }
.markdown-body :deep(cite.citation-ref) {
  font-style: normal;
  background: #e8f0fe;
  color: #1a56db;
  border-radius: 4px;
  padding: 0.1em 0.35em;
  font-size: 0.88em;
}

.citations {
  padding-top: 0.75rem;
  border-top: 1px solid #dee2e6;
}
.citation-chips { display: flex; flex-wrap: wrap; gap: 0.25rem; }

.message-metadata {
  padding-top: 0.5rem;
  border-top: 1px solid #dee2e6;
}
</style>
