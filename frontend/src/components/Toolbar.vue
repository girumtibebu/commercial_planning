<template>
  <div class="flex flex-wrap items-center gap-2 border-b border-outline-gray-2 bg-surface-white px-3 py-2">
    <template v-if="editable">
      <Button size="sm" @click="grid?.addLine()"><template #prefix><Icon name="plus" :size="12" /></template>Line</Button>
      <Button size="sm" @click="grid?.addCategory()"><template #prefix><Icon name="plus" :size="12" /></template>Category</Button>
      <Button size="sm" @click="grid?.addAdjustment()"><template #prefix><Icon name="plus" :size="12" /></template>Adjustment</Button>
      <span class="ml-1 hidden text-[11px] text-ink-gray-5 xl:inline">
        Enter edits · Ctrl+Enter new line · Shift+Enter details · Alt+arrows move
      </span>
    </template>
    <span v-else class="text-xs text-ink-gray-5">This version is read-only. Pick a Working version in the version menu to edit it.</span>

    <div class="ml-auto flex items-center gap-2">
      <Button size="sm" variant="ghost" @click="grid?.setAllCollapsed(true)">Collapse</Button>
      <Button size="sm" variant="ghost" @click="grid?.setAllCollapsed(false)">Expand</Button>
      <div class="relative">
        <Icon name="search" :size="13" class="pointer-events-none absolute left-2 top-2 text-ink-gray-5" />
        <input
          :value="search"
          class="h-7 w-48 rounded-md border border-outline-gray-3 bg-surface-white pl-7 pr-2 text-sm outline-none focus:border-outline-blue-3"
          placeholder="Search lines…"
          @input="$emit('update:search', $event.target.value)"
        />
      </div>
      <select
        :value="costType"
        class="h-7 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0 text-sm leading-normal"
        @change="$emit('update:costType', $event.target.value)"
      >
        <option value="">All cost types</option>
        <option v-for="type in costTypes" :key="type" :value="type">{{ type }}</option>
      </select>
    </div>
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import Icon from './Icon.vue'

defineProps({
  search: String,
  costType: String,
  costTypes: { type: Array, default: () => [] },
  editable: Boolean,
  grid: Object,
})
defineEmits(['update:search', 'update:costType'])
</script>
