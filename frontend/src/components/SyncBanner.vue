<template>
  <div v-if="notices.length" class="border-b border-outline-amber-3 bg-surface-amber-2 px-4 py-2 text-sm text-ink-amber-8">
    <div v-for="notice in notices" :key="notice.key" class="flex flex-wrap items-center gap-2 py-0.5">
      <span>{{ notice.text }}</span>
      <Button
        v-if="notice.action && editable"
        size="sm"
        variant="solid"
        :label="notice.action"
        @click="$emit(notice.event)"
      />
    </div>
    <div v-if="!editable && needsNewVersion" class="flex flex-wrap items-center gap-2 py-0.5">
      <span class="text-xs text-ink-amber-6">This version is read-only, so it was left as it is.</span>
      <Button size="sm" variant="solid" label="Create a new version with these changes" @click="$emit('newversion')" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Button } from 'frappe-ui'

const props = defineProps({ status: Object, editable: Boolean, source: String, fmt: Object })
defineEmits(['add', 'refresh', 'newversion'])

const LABELS = { qty: 'qty', uom: 'unit', selling: 'selling' }

function describe(change) {
  const parts = Object.keys(LABELS)
    .filter((key) => change[key])
    .map((key) => {
      const [from, to] = change[key]
      const show = key === 'selling' ? props.fmt.number : (value) => value || '—'
      return `${LABELS[key]} ${show(from)} → ${show(to)}`
    })
  return `${change.label}: ${parts.join(', ')}`
}

const needsNewVersion = computed(() => Boolean(props.status?.new_items.length || props.status?.changes.length))

const notices = computed(() => {
  const status = props.status
  if (!status || status.in_sync) return []
  const list = []
  const added = status.new_items
  if (added.length) {
    list.push({
      key: 'new',
      text: `${added.length} new item${added.length > 1 ? 's' : ''} on ${props.source} not in the plan: ${added
        .map((item) => item.label)
        .join(', ')}.`,
      action: `Add ${added.length > 1 ? 'them' : 'it'} to the plan`,
      event: 'add',
    })
  }
  if (status.changes.length) {
    list.push({
      key: 'changes',
      text: `${props.source} changed — ${status.changes.map(describe).join(' · ')}.`,
      action: `Refresh from ${props.source || 'document'}`,
      event: 'refresh',
    })
  }
  if (status.removed_items.length) {
    list.push({
      key: 'removed',
      text: `No longer on ${props.source}: ${status.removed_items.map((item) => item.label).join(', ')}. They keep their planned costs but no selling price.`,
    })
  }
  return list
})
</script>
