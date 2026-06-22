<!-- src/components/chat/CaseSelector.vue -->
<template>
  <div>
    <label class="form-label fw-bold">Case</label>
    <div v-if="casesStore.isLoading" class="text-muted small">Loading cases…</div>

    <select
      v-else
      class="form-select"
      :value="modelValue?.id ?? ''"
      @change="handleChange"
    >
      <option value="">— Select a case —</option>
      <option v-for="c in casesStore.cases" :key="c.id" :value="c.id">
        {{ c.title }} ({{ c.document_count }} docs)
      </option>
    </select>

    <div v-if="modelValue" class="mt-2">
      <small class="text-muted">
        <i class="bi bi-file-earmark me-1"></i>
        {{ modelValue.document_count }} document(s) in case
      </small>
    </div>

    <div v-if="casesStore.cases.length === 0 && !casesStore.isLoading" class="mt-2">
      <small class="text-warning">
        No cases yet.
        <router-link to="/cases">Create a case</router-link>
        to use this mode.
      </small>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useCasesStore } from '@/stores/cases'

const props = defineProps({
  modelValue: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue'])

const casesStore = useCasesStore()

onMounted(() => {
  casesStore.fetchCases()
})

const handleChange = (e) => {
  const id = parseInt(e.target.value)
  if (!id) { emit('update:modelValue', null); return }
  const found = casesStore.cases.find((c) => c.id === id) || null
  emit('update:modelValue', found)
}
</script>
