<template>
  <div class="relative h-full w-full">
    <input
      ref="input"
      v-model="text"
      class="w-full"
      autocomplete="off"
      @input="search"
      @keydown="onKey"
      @blur="onBlur"
    />
    <Teleport to="body">
      <ul
        v-if="open"
        class="fixed z-[2000] max-h-64 min-w-[280px] overflow-auto rounded-md border border-outline-gray-2 bg-surface-white py-1 text-sm shadow-xl"
        :style="position"
      >
        <li
          v-for="(option, index) in options"
          :key="option.value"
          :ref="(el) => index === highlighted && el?.scrollIntoView({ block: 'nearest' })"
          class="cursor-pointer px-3 py-1.5"
          :class="index === highlighted ? 'bg-surface-blue-2' : 'hover:bg-surface-gray-2'"
          @mousedown.prevent="choose(option)"
          @mousemove="highlighted = index"
        >
          <div class="font-medium text-ink-gray-9">{{ option.value }}</div>
          <div v-if="option.description" class="truncate text-xs text-ink-gray-5">{{ option.description }}</div>
        </li>
        <li v-if="!options.length" class="px-3 py-2 text-ink-gray-5">
          {{ loading ? 'Searching…' : 'No matches — pick an existing record' }}
        </li>
      </ul>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from '../api'

const props = defineProps({
  doctype: String,
  initial: { type: String, default: '' },
  keepCaret: Boolean,
})
const emit = defineEmits(['commit', 'cancel'])

const input = ref(null)
const text = ref(props.initial)
const options = ref([])
const highlighted = ref(0)
const loading = ref(true)
const anchor = ref({ left: 0, top: 0 })
let done = false
let timer
let latest = 0

const open = computed(() => !done && (options.value.length > 0 || Boolean(text.value.trim()) || loading.value))
const position = computed(() => ({ left: anchor.value.left + 'px', top: anchor.value.top + 'px' }))

function placeList() {
  const rect = input.value?.getBoundingClientRect()
  if (rect) anchor.value = { left: rect.left, top: rect.bottom + 2 }
}

onMounted(async () => {
  await nextTick()
  input.value?.focus()
  if (props.keepCaret) input.value?.setSelectionRange(text.value.length, text.value.length)
  else input.value?.select()
  placeList()
  fetchOptions(props.keepCaret ? text.value : '')
  window.addEventListener('scroll', placeList, true)
})

onBeforeUnmount(() => {
  clearTimeout(timer)
  window.removeEventListener('scroll', placeList, true)
})

async function fetchOptions(txt) {
  const ticket = ++latest
  loading.value = true
  const found = (await api.searchLink(props.doctype, txt)) || []
  if (ticket !== latest) return
  options.value = found
  highlighted.value = 0
  loading.value = false
  placeList()
}

function search() {
  clearTimeout(timer)
  timer = setTimeout(() => fetchOptions(text.value), 120)
}

function finish(kind, value) {
  if (done) return
  done = true
  emit(kind, value)
}

function choose(option) {
  finish('commit', option.value)
}

function onKey(event) {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    event.stopPropagation()
    const step = event.key === 'ArrowDown' ? 1 : -1
    highlighted.value = (highlighted.value + step + options.value.length) % Math.max(options.value.length, 1)
  } else if (event.key === 'Enter' || event.key === 'Tab') {
    event.preventDefault()
    event.stopPropagation()
    if (!text.value.trim()) return finish('commit', '')
    const picked = options.value[highlighted.value]
    if (picked && !loading.value) finish('commit', picked.value)
  } else if (event.key === 'Escape') {
    event.stopPropagation()
    finish('cancel')
  } else {
    event.stopPropagation()
  }
}

function onBlur() {
  setTimeout(() => finish('cancel'), 150)
}
</script>
