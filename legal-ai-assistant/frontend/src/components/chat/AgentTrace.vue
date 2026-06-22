<!-- src/components/chat/AgentTrace.vue -->
<template>
  <div v-if="trace" class="agent-trace mt-2">
    <button
      class="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1 trace-toggle"
      @click="open = !open"
    >
      <i class="bi bi-robot"></i>
      <span>Agent selected {{ trace.selected_docs?.length ?? 0 }} of {{ trace.total_docs }} docs</span>
      <i :class="open ? 'bi bi-chevron-up' : 'bi bi-chevron-down'" class="ms-1"></i>
    </button>

    <div v-if="open" class="trace-body mt-2 p-2 rounded border">
      <div v-if="trace.routing_reasoning" class="mb-2 text-muted small fst-italic">
        "{{ trace.routing_reasoning }}"
      </div>
      <div v-for="doc in trace.selected_docs" :key="doc.id" class="trace-doc mb-1">
        <span class="badge me-1" :class="fileTypeBadge(doc.file_type)">
          {{ doc.file_type?.toUpperCase() ?? 'DOC' }}
        </span>
        <strong>{{ doc.title }}</strong>
      </div>
      <div v-if="!trace.selected_docs?.length" class="text-muted small">
        No documents were routed — all documents were searched.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  trace: { type: Object, default: null },
})

const open = ref(false)

const fileTypeBadge = (ft) => {
  if (ft === 'image') return 'bg-warning text-dark'
  if (ft === 'pdf') return 'bg-danger'
  return 'bg-secondary'
}
</script>

<style scoped>
.agent-trace {
  font-size: 0.82rem;
}
.trace-toggle {
  font-size: 0.82rem;
  padding: 0.2rem 0.6rem;
}
.trace-body {
  background: #f8f9fa;
  font-size: 0.82rem;
}
.trace-doc {
  display: flex;
  align-items: center;
}
</style>
