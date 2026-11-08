<template>
  <AppShell>
    <div v-if="loading" class="flex flex-1 items-center justify-center text-ink-gray-5">Loading…</div>
    <div v-else-if="error" class="m-6 rounded-lg border border-outline-red-3 bg-surface-red-2 p-4 text-ink-red-8">{{ error }}</div>
    <RouterView v-else />
  </AppShell>

  <CreateVersionDialog
    v-if="ws"
    v-model="createOpen"
    :versions="ws.versions"
    :templates="ws.templates"
    :stages="ws.stages"
    :purposes="ws.purposes"
    :default-from="focusVersion?.name"
    :preset="createFrom"
    :apply-changes="createApply"
    @create="onCreate"
  />
  <ToastProvider />
</template>

<script setup>
import { computed, onMounted, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ToastProvider } from 'frappe-ui'
import AppShell from './components/AppShell.vue'
import CreateVersionDialog from './components/CreateVersionDialog.vue'
import { api } from './api'
import { makeFormatter } from './format'
import { useWorkspace } from './useWorkspace'

const router = useRouter()
const segments = window.location.pathname.split('/').filter(Boolean)
const planName = decodeURIComponent(segments[2] || '')
const query = new URLSearchParams(window.location.search)
const origin = { doctype: query.get('from'), name: query.get('name') }

const workspace = useWorkspace(planName)
const { ws, loading, error, load, createVersion, focusVersion } = workspace

const fmt = computed(() => makeFormatter(ws.value?.plan.currency))
const createOpen = ref(false)
const createFrom = ref(null)
const createApply = ref(false)

function openCreate(from = null, applyChanges = false) {
  createFrom.value = from
  createApply.value = applyChanges
  createOpen.value = true
}

async function onCreate({ done, ...args }) {
  const created = await createVersion(args)
  if (created) router.push({ name: 'plan', params: { plan: planName } })
  done(Boolean(created))
}

function deskPath(doctype, name) {
  return `/desk/${doctype.toLowerCase().replace(/ /g, '-')}/${encodeURIComponent(name)}`
}

function goToDesk() {
  const linked = ws.value?.plan.linked || []
  const target = (origin.doctype && origin.name && origin) || linked[linked.length - 1]
  window.location.href = target ? deskPath(target.doctype, target.name) : '/desk'
}

provide('cp', { planName, origin, fmt, openCreate, goToDesk, deskPath, ...workspace })

onMounted(async () => {
  await load()
  if (ws.value) api.logView(planName).catch(() => {})
})
</script>
