<template>
  <div class="flex h-full overflow-hidden bg-surface-gray-1 text-ink-gray-8">
    <div v-if="isMobile && drawerOpen" class="fixed inset-0 z-40 bg-black-overlay-200" @click="drawerOpen = false" />

    <!-- Sidebar -->
    <aside
      class="z-50 flex shrink-0 flex-col border-r border-outline-gray-2 bg-surface-gray-1 transition-all"
      :class="[
        rail ? 'w-[56px]' : 'w-[240px]',
        isMobile ? 'fixed inset-y-0 left-0 shadow-xl' : '',
        isMobile && !drawerOpen ? '-translate-x-full' : '',
      ]"
    >
      <div class="flex items-center gap-2.5 border-b border-outline-gray-2 p-3.5" :class="rail ? 'justify-center' : ''">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-surface-gray-9 text-[11px] font-bold text-ink-white">CP</span>
        <div v-if="!rail" class="min-w-0 leading-tight">
          <div class="truncate text-sm font-semibold text-ink-gray-9">Commercial Planning</div>
          <div class="text-[10px] uppercase tracking-widest text-ink-gray-5">Cost planning</div>
        </div>
        <button
          v-if="!rail"
          class="ml-auto flex h-6 w-6 items-center justify-center rounded border border-outline-gray-2 text-ink-gray-6 hover:bg-surface-gray-2"
          title="Back to Desk"
          @click="goToDesk"
        >
          <Icon name="close" :size="12" />
        </button>
      </div>

      <div v-if="!rail" class="px-4 pb-2 pt-4 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Workspace</div>
      <nav class="flex flex-col gap-0.5 px-2" :class="rail ? 'pt-3' : ''">
        <router-link
          v-for="page in PAGES"
          :key="page.key"
          :to="{ name: page.key, params: { plan: planName } }"
          custom
          v-slot="{ navigate, isActive }"
        >
          <button
            class="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm"
            :class="[
              isActive ? 'bg-surface-white font-medium text-ink-gray-9 shadow-sm ring-1 ring-outline-gray-2' : 'text-ink-gray-7 hover:bg-surface-gray-2',
              rail ? 'justify-center' : '',
            ]"
            :title="rail ? page.label : undefined"
            @click="navigate(); drawerOpen = false"
          >
            <Icon :name="page.icon" :size="15" />
            <span v-if="!rail" class="flex-1 text-left">{{ page.label }}</span>
            <span v-if="!rail && counts[page.key]" class="rounded-full bg-surface-gray-3 px-1.5 text-[10px] text-ink-gray-6">{{ counts[page.key] }}</span>
          </button>
        </router-link>
      </nav>

      <template v-if="!rail && ws">
        <div class="px-4 pb-2 pt-5 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Linked documents</div>
        <div class="flex flex-col gap-1.5 px-2.5">
          <a
            v-for="doc in ws.plan.linked"
            :key="doc.doctype + doc.name"
            :href="deskPath(doc.doctype, doc.name)"
            class="group rounded-lg border bg-surface-white px-3 py-2 hover:border-outline-gray-4"
            :class="isOrigin(doc) ? 'border-outline-blue-3' : 'border-outline-gray-2'"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="text-[11px] font-medium uppercase tracking-wide text-ink-gray-5">{{ doc.doctype }}</span>
              <Icon name="external" :size="11" class="text-ink-gray-4 group-hover:text-ink-gray-7" />
            </div>
            <div class="mt-0.5 truncate font-mono text-xs text-ink-gray-9">{{ doc.name }}</div>
            <div class="mt-1.5 flex items-center gap-1.5">
              <Badge v-if="doc.status" :label="doc.status" theme="gray" size="sm" />
              <Badge v-if="isOrigin(doc)" label="Opened from" theme="blue" size="sm" />
            </div>
          </a>
          <div v-if="!ws.plan.linked.length" class="px-1 text-xs text-ink-gray-5">Nothing linked yet.</div>
        </div>

        <div class="px-4 pb-2 pt-5 text-[10px] font-semibold uppercase tracking-widest text-ink-gray-5">Current plan</div>
        <div class="mx-2.5 rounded-lg border border-outline-gray-2 bg-surface-white p-3">
          <div class="text-xs font-semibold text-ink-gray-9">{{ ws.plan.title }}</div>
          <div class="mt-0.5 font-mono text-[11px] text-ink-gray-5">{{ ws.plan.name }}</div>
          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <Badge :label="ws.plan.current_stage" theme="blue" size="sm" />
            <Badge :label="ws.plan.status" theme="gray" size="sm" />
          </div>
          <div class="mt-2 text-[11px] text-ink-gray-5">{{ ws.plan.company }} · {{ ws.plan.currency }}</div>
        </div>
      </template>

      <div class="mt-auto flex items-center gap-2 border-t border-outline-gray-2 px-3 py-2.5" :class="rail ? 'justify-center' : ''">
        <Avatar :label="userName" size="sm" />
        <div v-if="!rail" class="min-w-0">
          <div class="truncate text-xs font-medium text-ink-gray-8">{{ userName }}</div>
          <div class="text-[11px] text-ink-gray-5">{{ roleLabel }}</div>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-[52px] shrink-0 items-center gap-2.5 border-b border-outline-gray-2 bg-surface-white px-4">
        <button
          v-if="isMobile"
          class="flex h-8 w-8 items-center justify-center rounded-md border border-outline-gray-2 text-ink-gray-6"
          @click="drawerOpen = !drawerOpen"
        >
          <Icon name="menu" :size="15" />
        </button>
        <button
          class="flex h-7 items-center gap-1.5 rounded-md border border-outline-gray-2 bg-surface-white px-2.5 text-xs font-medium text-ink-gray-7 hover:bg-surface-gray-1"
          @click="goToDesk"
        >
          <Icon name="back" :size="12" /> <span class="hidden sm:inline">Desk</span>
        </button>
        <Icon name="chevright" :size="12" class="text-ink-gray-4" />
        <div class="min-w-0 truncate text-sm font-semibold text-ink-gray-9">{{ ws?.plan.title || planName }}</div>
        <Badge v-if="ws" :label="ws.plan.current_stage" theme="blue" />

        <div class="ml-auto flex items-center gap-2">
          <span class="hidden text-xs text-ink-gray-5 md:inline">{{ saving ? 'Saving…' : ws ? 'All changes saved' : '' }}</span>
          <template v-if="ws">
            <span
              v-if="ws.columns.length > 1"
              class="hidden items-center gap-1 rounded-md bg-surface-blue-2 px-2 py-1 text-xs text-ink-blue-8 md:flex"
            >
              <Icon name="compare" :size="12" /> Comparing {{ ws.columns.length }}
            </span>
            <VersionSwitcher />
            <Button size="sm" variant="solid" :disabled="!ws.plan.can_write" @click="openCreate(null)">
              <template #prefix><Icon name="plus" :size="13" /></template>
              New version
            </Button>
          </template>
        </div>
      </header>

      <main class="flex min-h-0 flex-1 flex-col overflow-hidden bg-surface-gray-1">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { Avatar, Badge, Button } from 'frappe-ui'
import Icon from './Icon.vue'
import VersionSwitcher from './VersionSwitcher.vue'
import { PAGES } from '../router'

const { ws, planName, origin, saving, goToDesk, deskPath, openCreate } = inject('cp')

const userName = window.user_fullname || window.user || 'You'
const roleLabel = 'Planner'

const drawerOpen = ref(false)
const isMobile = ref(false)
const isTablet = ref(false)
const rail = computed(() => isTablet.value && !isMobile.value)

function check() {
  isMobile.value = window.innerWidth < 768
  isTablet.value = window.innerWidth >= 768 && window.innerWidth < 1100
}
onMounted(() => {
  check()
  window.addEventListener('resize', check)
})
onBeforeUnmount(() => window.removeEventListener('resize', check))

const isOrigin = (doc) => origin.doctype === doc.doctype && origin.name === doc.name
const counts = computed(() => ({ versions: ws.value?.versions.length || 0 }))
</script>
