<template>
  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-lg font-semibold text-ink-gray-9">Versions</h1>
        <p class="text-xs text-ink-gray-5">Every state of this job's plan. Tick versions to compare them side by side.</p>
      </div>
      <Button variant="solid" :disabled="!ws.plan.can_write" @click="openCreate(null)">
        <template #prefix><Icon name="plus" :size="13" /></template>
        New version
      </Button>
    </div>

    <div class="overflow-x-auto rounded-lg border border-outline-gray-2 bg-surface-white">
      <table class="w-full min-w-[900px] text-sm tabular-nums">
        <thead>
          <tr class="border-b border-outline-gray-1 bg-surface-gray-1 text-[11px] uppercase tracking-wide text-ink-gray-5">
            <th class="w-10 px-3 py-2"></th>
            <th class="px-3 py-2 text-left font-medium">Version</th>
            <th class="px-3 py-2 text-left font-medium">Stage · purpose</th>
            <th class="px-3 py-2 text-left font-medium">Status</th>
            <th class="px-3 py-2 text-right font-medium">Cost</th>
            <th class="px-3 py-2 text-right font-medium">Selling</th>
            <th class="px-3 py-2 text-right font-medium">Profit</th>
            <th class="px-3 py-2 text-right font-medium">Margin</th>
            <th class="px-3 py-2 text-left font-medium">Created</th>
            <th class="w-10 px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="ver in ordered" :key="ver.name" class="group border-b border-outline-gray-1 last:border-0 hover:bg-surface-gray-1">
            <td class="px-3 py-2.5">
              <input type="checkbox" class="cursor-pointer" :checked="shown.has(ver.name)" @change="toggleColumn(ver.name)" />
            </td>
            <td class="px-3 py-2.5">
              <button class="text-left" @click="open(ver.name)">
                <span class="font-semibold text-ink-gray-9">V{{ ver.version_no }}</span>
                <span class="ml-1.5 text-ink-gray-8">{{ ver.version_name }}</span>
                <span v-if="ver.name === focusVersion?.name" class="ml-2 text-[10px] font-medium uppercase tracking-wide text-ink-blue-6">open</span>
              </button>
              <div v-if="ver.reason" class="mt-0.5 max-w-[320px] truncate text-xs text-ink-gray-5" :title="ver.reason">“{{ ver.reason }}”</div>
            </td>
            <td class="px-3 py-2.5 text-ink-gray-7">{{ ver.stage }} · {{ ver.purpose }}</td>
            <td class="px-3 py-2.5">
              <div class="flex flex-wrap items-center gap-1">
                <Badge :label="ver.status" :theme="statusTheme(ver.status)" size="sm" />
                <Badge v-if="ver.reference_role" :label="ver.reference_role" theme="blue" size="sm" />
              </div>
            </td>
            <td class="px-3 py-2.5 text-right">{{ fmt.number(ver.total_cost) }}</td>
            <td class="px-3 py-2.5 text-right">{{ fmt.number(ver.total_selling) }}</td>
            <td class="px-3 py-2.5 text-right" :class="ver.total_profit < 0 ? 'text-ink-red-6' : ''">{{ fmt.number(ver.total_profit) }}</td>
            <td class="px-3 py-2.5 text-right">{{ fmt.percent(ver.margin_pct) }}</td>
            <td class="px-3 py-2.5 text-xs text-ink-gray-6">
              {{ ownerName(ver.owner) }}<br /><span class="text-ink-gray-5" :title="fullDate(ver.creation)">{{ timeAgo(ver.creation) }}</span>
            </td>
            <td class="px-3 py-2.5 text-right">
              <Dropdown :options="menu(ver)" placement="right">
                <button class="flex h-7 w-7 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-3">
                  <Icon name="dots" :size="14" />
                </button>
              </Dropdown>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="compared.length > 1" class="rounded-lg border border-outline-gray-2 bg-surface-white">
      <div class="border-b border-outline-gray-1 px-4 py-2.5 text-sm font-semibold text-ink-gray-9">Comparison</div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm tabular-nums">
          <thead>
            <tr class="bg-surface-gray-1 text-[11px] uppercase tracking-wide text-ink-gray-5">
              <th class="px-4 py-2 text-left font-medium"></th>
              <th v-for="ver in compared" :key="ver.name" class="px-4 py-2 text-right font-medium">V{{ ver.version_no }} {{ ver.version_name }}</th>
              <th class="px-4 py-2 text-right font-medium">Δ vs first</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="metric in metrics" :key="metric.key" class="border-t border-outline-gray-1">
              <td class="px-4 py-2 text-ink-gray-6">{{ metric.label }}</td>
              <td v-for="ver in compared" :key="ver.name" class="px-4 py-2 text-right">{{ metric.show(ver[metric.key]) }}</td>
              <td class="px-4 py-2 text-right" :class="deltaTone(metric, delta(metric))">{{ metric.pct ? delta(metric).toFixed(1) + ' pts' : fmt.signed(delta(metric)) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Dialog v-model="reopenOpen" :options="{ title: 'Reopen version', size: 'md' }">
      <template #body-content>
        <label class="mb-1 block text-sm text-ink-gray-7">Reason (recorded in the audit trail)</label>
        <textarea v-model="reason" rows="3" class="w-full rounded-md border border-outline-gray-3 p-2 text-sm" />
        <div class="mt-4 flex justify-end gap-2">
          <Button label="Cancel" @click="reopenOpen = false" />
          <Button variant="solid" label="Reopen" :disabled="!reason.trim()" @click="doReopen" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, inject, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, Dialog, Dropdown } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import { fullDate, timeAgo } from '../format'

const { ws, planName, fmt, focusVersion, focusOn, toggleColumn, openCreate, setRole, freeze, approve, reopen } = inject('cp')
const router = useRouter()

const shown = computed(() => new Set(ws.value.columns.map((column) => column.version)))
const ordered = computed(() => [...ws.value.versions].sort((a, b) => b.version_no - a.version_no))
const compared = computed(() => ws.value.versions.filter((ver) => shown.value.has(ver.name)).sort((a, b) => a.version_no - b.version_no))

const statusTheme = (status) => ({ Working: 'green', Frozen: 'gray', Approved: 'blue' })[status] || 'gray'
const ownerName = (user) => (user || '').split('@')[0]

const metrics = [
  { key: 'total_cost', label: 'Internal cost', show: fmt.value.number, bad: 'up' },
  { key: 'total_selling', label: 'Client selling', show: fmt.value.number },
  { key: 'total_profit', label: 'Profit', show: fmt.value.number, bad: 'down' },
  { key: 'margin_pct', label: 'Margin', show: (v) => fmt.value.percent(v), pct: true, bad: 'down' },
]

function delta(metric) {
  const list = compared.value
  return (list[list.length - 1][metric.key] || 0) - (list[0][metric.key] || 0)
}

function deltaTone(metric, value) {
  if (!value || !metric.bad) return 'text-ink-gray-6'
  const worse = metric.bad === 'up' ? value > 0 : value < 0
  return worse ? 'text-ink-red-6' : 'text-ink-green-6'
}

async function open(name) {
  await focusOn(name)
  router.push({ name: 'plan', params: { plan: planName } })
}

const reopenOpen = ref(false)
const reopenTarget = ref(null)
const reason = ref('')

async function doReopen() {
  reopenOpen.value = false
  await reopen(reopenTarget.value, reason.value)
  reason.value = ''
}

function menu(ver) {
  const items = [
    { label: ver.can_edit ? 'Open and edit' : 'Open', onClick: () => open(ver.name) },
    { label: `New version from V${ver.version_no}…`, onClick: () => openCreate(ver.name) },
  ]
  if (ver.can_freeze) items.push({ label: 'Freeze', onClick: () => freeze(ver.name) })
  if (ver.can_approve) items.push({ label: 'Approve', onClick: () => approve(ver.name) })
  if (ver.can_reopen) {
    items.push({
      label: 'Reopen…',
      onClick: () => {
        reopenTarget.value = ver.name
        reopenOpen.value = true
      },
    })
  }
  for (const role of ['Baseline', 'Budget', 'Forecast']) {
    if (ver.reference_role !== role && ver.can_set_role?.[role]) items.push({ label: `Set as ${role}`, onClick: () => setRole(ver.name, role) })
  }
  if (ver.reference_role && ver.can_set_role?.[ver.reference_role]) {
    items.push({ label: `Clear ${ver.reference_role}`, onClick: () => setRole(ver.name, '') })
  }
  return items
}
</script>
