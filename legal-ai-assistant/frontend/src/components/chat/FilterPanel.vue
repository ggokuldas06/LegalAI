<!-- src/components/chat/FilterPanel.vue -->
<template>
  <div class="filter-panel card">
    <div class="card-body">
      <h6 class="card-title">
        <i class="bi bi-funnel me-2"></i>
        Filters (Mode C)
      </h6>
      
      <div class="mb-3">
        <label class="form-label">Jurisdiction</label>
        <select v-model="localFilters.jurisdiction" class="form-select form-select-sm">
          <option value="">All</option>
          <option value="US">United States</option>
          <option value="US-CA">California</option>
          <option value="US-NY">New York</option>
          <option value="EU">European Union</option>
          <option value="UK">United Kingdom</option>
        </select>
      </div>
      
      <div class="mb-3">
        <label class="form-label">Year Range</label>
        <div class="row g-2">
          <div class="col-6">
            <input
              v-model.number="localFilters.year_from"
              type="number"
              class="form-control form-control-sm"
              placeholder="From"
              min="1900"
              :max="currentYear"
            >
          </div>
          <div class="col-6">
            <input
              v-model.number="localFilters.year_to"
              type="number"
              class="form-control form-control-sm"
              placeholder="To"
              min="1900"
              :max="currentYear"
            >
          </div>
        </div>
      </div>
      
      <div class="mb-3">
        <label class="form-label">Include Keywords</label>
        <input
          v-model="includeKeywordsInput"
          type="text"
          class="form-control form-control-sm"
          placeholder="Comma-separated"
          @blur="updateIncludeKeywords"
        >
        <div class="mt-2">
          <span
            v-for="(keyword, idx) in localFilters.include"
            :key="idx"
            class="badge bg-success me-1 mb-1"
          >
            {{ keyword }}
            <i class="bi bi-x-circle ms-1" style="cursor: pointer" @click="removeIncludeKeyword(idx)"></i>
          </span>
        </div>
      </div>
      
      <div class="mb-3">
        <label class="form-label">Exclude Keywords</label>
        <input
          v-model="excludeKeywordsInput"
          type="text"
          class="form-control form-control-sm"
          placeholder="Comma-separated"
          @blur="updateExcludeKeywords"
        >
        <div class="mt-2">
          <span
            v-for="(keyword, idx) in localFilters.exclude"
            :key="idx"
            class="badge bg-danger me-1 mb-1"
          >
            {{ keyword }}
            <i class="bi bi-x-circle ms-1" style="cursor: pointer" @click="removeExcludeKeyword(idx)"></i>
          </span>
        </div>
      </div>
      
      <button
        class="btn btn-sm btn-outline-secondary w-100"
        @click="resetFilters"
      >
        <i class="bi bi-arrow-counterclockwise me-1"></i>
        Reset Filters
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])

const currentYear = new Date().getFullYear()

const localFilters = ref({ ...props.modelValue })
const includeKeywordsInput = ref(props.modelValue.include?.join(', ') || '')
const excludeKeywordsInput = ref(props.modelValue.exclude?.join(', ') || '')

const updateIncludeKeywords = () => {
  if (includeKeywordsInput.value.trim()) {
    localFilters.value.include = includeKeywordsInput.value
      .split(',')
      .map(k => k.trim())
      .filter(k => k)
    emitUpdate()
  }
}

const updateExcludeKeywords = () => {
  if (excludeKeywordsInput.value.trim()) {
    localFilters.value.exclude = excludeKeywordsInput.value
      .split(',')
      .map(k => k.trim())
      .filter(k => k)
    emitUpdate()
  }
}

const removeIncludeKeyword = (index) => {
  localFilters.value.include.splice(index, 1)
  includeKeywordsInput.value = localFilters.value.include.join(', ')
  emitUpdate()
}

const removeExcludeKeyword = (index) => {
  localFilters.value.exclude.splice(index, 1)
  excludeKeywordsInput.value = localFilters.value.exclude.join(', ')
  emitUpdate()
}

const resetFilters = () => {
  localFilters.value = {
    jurisdiction: '',
    year_from: null,
    year_to: null,
    include: [],
    exclude: [],
  }
  includeKeywordsInput.value = ''
  excludeKeywordsInput.value = ''
  emitUpdate()
}

const emitUpdate = () => {
  emit('update:modelValue', { ...localFilters.value })
}

// Watch for changes in select and number inputs
watch(
  () => [localFilters.value.jurisdiction, localFilters.value.year_from, localFilters.value.year_to],
  () => {
    emitUpdate()
  }
)
</script>

<style scoped>
.filter-panel {
  border: 1px solid #dee2e6;
}

.badge {
  cursor: default;
}

.badge i {
  cursor: pointer;
}
</style>