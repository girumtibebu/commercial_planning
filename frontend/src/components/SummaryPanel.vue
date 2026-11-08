<template>
  <div class="grid gap-3 md:grid-cols-[minmax(190px,1.1fr)_minmax(0,3fr)]">
    <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
      <div class="text-[11px] font-semibold uppercase tracking-widest text-ink-blue-8">Client selling price</div>
      <div class="mt-1 text-2xl font-semibold tabular-nums text-ink-gray-9">{{ fmt.money(summary.selling) }}</div>
      <div class="text-xs text-ink-gray-5">{{ fmt.currency }}</div>
    </div>

    <div class="overflow-x-auto rounded-lg border border-outline-gray-2 bg-surface-white">
      <table class="w-full text-sm tabular-nums">
        <thead>
          <tr class="border-b border-outline-gray-1 bg-surface-gray-1 text-[11px] uppercase tracking-wide text-ink-gray-5">
            <th class="px-4 py-1.5 text-left font-medium"></th>
            <th v-for="column in columns" :key="column.key" class="px-4 py-1.5 text-right font-medium">{{ column.label }}</th>
          </tr>
        </thead>
        <tbody>
          <tr class="border-b border-outline-gray-1">
            <td class="px-4 py-1.5 text-xs font-medium text-ink-amber-8">Internal cost</td>
            <td v-for="column in columns" :key="column.key" class="px-4 py-1.5 text-right">{{ fmt.money(summary.costs[column.key]) }}</td>
          </tr>
          <tr class="border-b border-outline-gray-1">
            <td class="px-4 py-1.5 text-xs font-medium text-ink-green-8">Profit</td>
            <td v-for="column in columns" :key="column.key" class="px-4 py-1.5 text-right" :class="tone(summary.profit[column.key])">
              {{ fmt.money(summary.profit[column.key]) }}
            </td>
          </tr>
          <tr>
            <td class="px-4 py-1.5 text-xs font-medium text-ink-green-8">Margin</td>
            <td v-for="column in columns" :key="column.key" class="px-4 py-1.5 text-right" :class="tone(summary.margin[column.key])">
              {{ fmt.percent(summary.margin[column.key]) }}
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="variances.length" class="flex flex-wrap items-center gap-1.5 border-t border-outline-gray-1 px-4 py-2">
        <span class="text-[11px] font-medium uppercase tracking-wide text-ink-gray-5">Cost variance</span>
        <span
          v-for="item in variances"
          :key="item.label"
          class="rounded px-2 py-0.5 text-xs tabular-nums"
          :class="item.value > 0 ? 'bg-surface-red-2 text-ink-red-6' : 'bg-surface-green-2 text-ink-green-6'"
        >
          {{ item.label }} {{ fmt.signed(item.value) }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ summary: Object, fmt: Object })

const columns = [
  { key: 'quotation', label: 'Quotation' },
  { key: 'budget', label: 'Budget' },
  { key: 'forecast', label: 'Forecast' },
  { key: 'actual', label: 'Actual' },
]

const LABELS = {
  budget_vs_quotation: 'Budget vs Quotation',
  forecast_vs_budget: 'Forecast vs Budget',
  actual_vs_forecast: 'Actual vs Forecast',
  actual_vs_quotation: 'Actual vs Quotation',
}

const variances = computed(() =>
  Object.entries(props.summary.variance)
    .filter(([, value]) => value != null)
    .map(([key, value]) => ({ label: LABELS[key], value })),
)

const tone = (value) => (value == null ? 'text-ink-gray-5' : value < 0 ? 'text-ink-red-6' : 'text-ink-green-6')
</script>
