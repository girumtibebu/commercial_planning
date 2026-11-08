<template>
  <div ref="root" class="relative">
    <button
      class="flex h-8 items-center gap-2 rounded-md border border-outline-gray-3 bg-surface-white px-2.5 text-sm hover:bg-surface-gray-1"
      :class="open ? 'border-outline-blue-3 bg-surface-blue-2' : ''"
      @click="open = !open"
    >
      <Icon name="layers" :size="14" class="text-ink-gray-6" />
      <template v-if="focusVersion">
        <span class="font-medium text-ink-gray-9">V{{ focusVersion.version_no }}</span>
        <span class="max-w-[150px] truncate text-ink-gray-7">{{ focusVersion.version_name }}</span>
        <Badge :label="focusVersion.status" :theme="statusTheme(focusVersion.status)" size="sm" />
      </template>
      <Icon name="chevdown" :size="12" class="text-ink-gray-5" />
    </button>

    <div
      v-if="open"
      class="absolute right-0 top-10 z-50 w-[340px] rounded-lg border border-outline-gray-2 bg-surface-white p-1.5 shadow-xl"
    >
      <div class="px-2 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">Versions</div>
      <div class="max-h-[340px] overflow-y-auto">
        <div
          v-for="ver in ordered"
          :key="ver.name"
          class="flex items-start gap-2 rounded-md px-2 py-1.5 hover:bg-surface-gray-1"
          :class="ver.name === focusVersion?.name ? 'bg-surface-blue-2' : ''"
        >
          <input
            type="checkbox"
            class="mt-1 cursor-pointer"
            :checked="shown.has(ver.name)"
            :title="shown.has(ver.name) ? 'Hide comparison column' : 'Compare as a column'"
            @change="toggleColumn(ver.name)"
          />
          <button class="min-w-0 flex-1 text-left" @click="pick(ver.name)">
            <div class="flex items-center gap-1.5">
              <span class="font-medium text-ink-gray-9">V{{ ver.version_no }}</span>
              <span class="truncate text-ink-gray-8">{{ ver.version_name }}</span>
              <Badge v-if="ver.reference_role" :label="ver.reference_role" theme="blue" size="sm" />
              <Badge :label="ver.status" :theme="statusTheme(ver.status)" size="sm" />
            </div>
            <div class="mt-0.5 text-[11px] text-ink-gray-5">{{ ver.stage }} · {{ ver.purpose }} · {{ fmt.compact(ver.total_cost) }} cost</div>
          </button>
        </div>
      </div>
      <div class="mt-1 border-t border-outline-gray-1 pt-1">
        <button
          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
          :disabled="!ws.plan.can_write"
          @click="create(null)"
        >
          <Icon name="plus" :size="13" /> New version…
        </button>
        <button
          v-if="focusVersion"
          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
          :disabled="!ws.plan.can_write"
          @click="create(focusVersion.name)"
        >
          <Icon name="copy" :size="13" /> New from V{{ focusVersion.version_no }}…
        </button>
        <router-link
          :to="{ name: 'versions', params: { plan: planName } }"
          class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
          @click="open = false"
        >
          <Icon name="compare" :size="13" /> Manage and compare versions
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { Badge } from 'frappe-ui'
import Icon from './Icon.vue'

const { ws, planName, fmt, focusVersion, focusOn, toggleColumn, openCreate } = inject('cp')

const open = ref(false)
const root = ref(null)

const shown = computed(() => new Set(ws.value.columns.map((column) => column.version)))
const ordered = computed(() => [...ws.value.versions].sort((a, b) => b.version_no - a.version_no))
const statusTheme = (status) => ({ Working: 'green', Frozen: 'gray', Approved: 'blue' })[status] || 'gray'

async function pick(name) {
  open.value = false
  await focusOn(name)
}

function create(from) {
  open.value = false
  openCreate(from)
}

const away = (event) => {
  if (open.value && root.value && !root.value.contains(event.target)) open.value = false
}
onMounted(() => document.addEventListener('mousedown', away))
onBeforeUnmount(() => document.removeEventListener('mousedown', away))
</script>
