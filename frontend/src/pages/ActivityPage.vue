<template>
  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-lg font-semibold text-ink-gray-9">Activity</h1>
        <p class="text-xs text-ink-gray-5">Who created, opened, changed and commented on this plan.</p>
      </div>
      <select v-model="scope" class="h-8 rounded-md border border-outline-gray-3 bg-surface-white px-2 py-0 text-sm leading-normal" @change="load">
        <option value="">Whole plan</option>
        <option v-for="ver in ws.versions" :key="ver.name" :value="ver.name">V{{ ver.version_no }} {{ ver.version_name }}</option>
      </select>
    </div>

    <div class="rounded-lg border border-outline-gray-2 bg-surface-white">
      <div v-if="loading && !events.length" class="p-10 text-center text-sm text-ink-gray-5">Loading activity…</div>
      <div v-else-if="failure" class="p-10 text-center text-sm text-ink-red-6">{{ failure }}</div>
      <div v-else-if="!events.length" class="p-10 text-center text-sm text-ink-gray-5">No activity yet.</div>

      <ol v-else class="px-5 py-3">
        <li v-for="(event, index) in events" :key="event.id" class="relative flex gap-3 pb-4">
          <div class="flex flex-col items-center">
            <Avatar :label="event.owner_full_name" size="md" />
            <div v-if="index < events.length - 1" class="mt-1 w-px flex-1 bg-outline-gray-2" />
          </div>
          <div class="min-w-0 flex-1 pt-0.5">
            <div class="flex flex-wrap items-center gap-1.5 text-sm">
              <span class="font-semibold text-ink-gray-9">{{ event.owner_full_name }}</span>
              <span class="text-ink-gray-5">·</span>
              <span class="text-xs text-ink-gray-5" :title="fullDate(event.creation)">{{ timeAgo(event.creation) }}</span>
              <Badge v-if="KIND[event.type]" :label="KIND[event.type].label" :theme="KIND[event.type].theme" size="sm" />
              <span v-if="event.version" class="rounded bg-surface-gray-2 px-1.5 text-[10px] text-ink-gray-6">{{ event.version }}</span>
            </div>

            <div
              v-if="event.html"
              class="mt-1 rounded-md border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-sm text-ink-gray-8"
              v-html="event.summary"
            />
            <div v-else class="mt-0.5 text-sm text-ink-gray-7">{{ event.summary }}</div>
            <div v-if="event.detail" class="mt-0.5 text-xs italic text-ink-gray-5">“{{ event.detail }}”</div>

            <template v-if="event.changes?.length > 1 || (event.changes?.length === 1 && expanded.has(event.id))">
              <button class="mt-1 text-xs text-ink-blue-6 hover:underline" @click="toggle(event.id)">
                {{ expanded.has(event.id) ? 'Hide changes' : `View ${event.changes.length} changes` }}
              </button>
              <ul v-if="expanded.has(event.id)" class="mt-1.5 rounded-md border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 font-mono text-[11.5px] leading-relaxed text-ink-gray-7">
                <li v-for="(line, i) in event.changes" :key="i">{{ line }}</li>
              </ul>
            </template>
          </div>
        </li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { Avatar, Badge } from 'frappe-ui'
import { api } from '../api'
import { fullDate, timeAgo } from '../format'

const { ws, planName } = inject('cp')

const KIND = {
  change: { label: 'change', theme: 'amber' },
  created: { label: 'version', theme: 'blue' },
  comment: { label: 'comment', theme: 'gray' },
  view: { label: 'opened', theme: 'gray' },
  assign: { label: 'assigned', theme: 'green' },
  info: { label: 'note', theme: 'gray' },
}

const scope = ref('')
const events = ref([])
const loading = ref(true)
const failure = ref('')
const expanded = ref(new Set())
let timer

async function load() {
  loading.value = true
  failure.value = ''
  try {
    events.value = await api.getActivity(planName, scope.value)
  } catch (err) {
    failure.value = err?.messages?.[0] || err?.message || 'Could not load activity'
  } finally {
    loading.value = false
  }
}

function toggle(id) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

onMounted(() => {
  load()
  timer = setInterval(load, 30000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>
