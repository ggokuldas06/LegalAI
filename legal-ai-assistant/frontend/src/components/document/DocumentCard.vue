<!-- src/components/document/DocumentCard.vue -->
<template>
  <div class="document-card card h-100">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-start mb-3">
        <div class="doc-icon">
          <i :class="iconClass"></i>
        </div>
        <span :class="`badge bg-${typeColor}`">{{ document.doctype }}</span>
      </div>
      
      <h5 class="card-title">{{ document.title }}</h5>
      
      <div class="card-text">
        <div class="doc-meta">
          <small v-if="document.jurisdiction" class="text-muted">
            <i class="bi bi-geo-alt me-1"></i>
            {{ document.jurisdiction }}
          </small>
          <small v-if="document.date" class="text-muted">
            <i class="bi bi-calendar me-1"></i>
            {{ formatDate(document.date) }}
          </small>
          <small class="text-muted">
            <i class="bi bi-file-earmark me-1"></i>
            {{ document.chunk_count || 0 }} chunks
          </small>
        </div>
      </div>
    </div>
    
    <div class="card-footer bg-transparent">
      <div class="btn-group w-100" role="group">
        <button
          class="btn btn-sm btn-outline-primary"
          @click="$emit('view', document)"
          title="View"
        >
          <i class="bi bi-eye"></i>
        </button>
        <button
          class="btn btn-sm btn-outline-success"
          @click="$emit('ingest', document.id)"
          title="Ingest for RAG"
        >
          <i class="bi bi-database"></i>
        </button>
        <button
          class="btn btn-sm btn-outline-danger"
          @click="$emit('delete', document.id)"
          title="Delete"
        >
          <i class="bi bi-trash"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  document: {
    type: Object,
    required: true,
  },
})

defineEmits(['delete', 'ingest', 'view'])

const iconClass = computed(() => {
  const icons = {
    contract: 'bi bi-file-earmark-text',
    case: 'bi bi-briefcase',
    regulation: 'bi bi-file-earmark-ruled',
    statute: 'bi bi-book',
    other: 'bi bi-file-earmark',
  }
  return `${icons[props.document.doctype] || icons.other} fs-3`
})

const typeColor = computed(() => {
  const colors = {
    contract: 'primary',
    case: 'success',
    regulation: 'warning',
    statute: 'info',
    other: 'secondary',
  }
  return colors[props.document.doctype] || colors.other
})

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString()
}
</script>

<style scoped>
.document-card {
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.document-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.doc-icon {
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
  border-radius: 8px;
  color: #495057;
}

.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.doc-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.card-footer {
  border-top: 1px solid #dee2e6;
}
</style>