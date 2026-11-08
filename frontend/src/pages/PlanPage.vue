<template>
  <div class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-5">
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-lg font-semibold text-ink-gray-9">Cost plan</h1>
        <p class="text-xs text-ink-gray-5">
          Build the internal cost behind each quotation item, compare versions, and watch the margin.
        </p>
      </div>
      <VersionBar :focus="focusVersion" :templates="ws.templates" @freeze="freeze" @approve="approve" @reopen="reopen" />
    </div>

    <div
      v-if="ws.plan.created_from === 'Project' && !ws.plan.sales_order"
      class="rounded-lg border border-outline-blue-1 bg-surface-blue-2 px-4 py-2 text-sm text-ink-blue-8"
    >
      This project has no Sales Order, so there is no client selling price to compare against — costs only.
    </div>

    <SyncBanner
      :status="ws.sync[focusVersion?.name]"
      :editable="Boolean(focusVersion?.can_edit)"
      :source="focusVersion?.source_name || 'the document'"
      :fmt="fmt"
      class="overflow-hidden rounded-lg border"
      @newversion="openCreate(focusVersion.name, true)"
      @add="send(focusVersion.name, [{ op: 'sync_source' }])"
      @refresh="send(focusVersion.name, [{ op: 'refresh_source' }])"
    />

    <SummaryPanel :summary="ws.summary" :fmt="fmt" />

    <div class="flex min-h-[420px] flex-1 flex-col overflow-hidden rounded-lg border border-outline-gray-2 bg-surface-white">
      <Toolbar
        v-model:search="search"
        v-model:cost-type="costType"
        :cost-types="costTypes"
        :editable="Boolean(focusVersion?.can_edit)"
        :grid="grid"
      />
      <div class="min-h-0 flex-1">
        <SheetGrid
          ref="grid"
          :ws="ws"
          :focus="focusVersion"
          :fmt="fmt"
          :send="send"
          :search="search"
          :cost-type="costType"
          @details="openDetails"
        />
      </div>
      <button
        v-if="focusVersion?.can_edit"
        class="flex items-center gap-2 border-t border-outline-gray-1 px-4 py-2 text-left text-sm text-ink-gray-5 hover:bg-surface-gray-1 hover:text-ink-gray-8"
        @click="grid?.addLine()"
      >
        <Icon name="plus" :size="13" /> Add cost line
      </button>
    </div>

    <LineDetailsDialog
      v-model="detailsOpen"
      :row="detailsRow"
      :version="focusVersion?.name"
      :editable="Boolean(focusVersion?.can_edit)"
      @save="saveDetails"
    />
  </div>
</template>

<script setup>
import { inject, ref } from 'vue'
import Icon from '../components/Icon.vue'
import LineDetailsDialog from '../components/LineDetailsDialog.vue'
import SheetGrid from '../components/SheetGrid.vue'
import SummaryPanel from '../components/SummaryPanel.vue'
import SyncBanner from '../components/SyncBanner.vue'
import Toolbar from '../components/Toolbar.vue'
import VersionBar from '../components/VersionBar.vue'

const { ws, fmt, focusVersion, send, freeze, approve, reopen, openCreate } = inject('cp')

const grid = ref(null)
const search = ref('')
const costType = ref('')
const detailsOpen = ref(false)
const detailsRow = ref(null)

const costTypes = ['Vendor', 'Internal Service', 'Equipment', 'Material', 'Labor', 'Transport', 'Subcontract', 'Stock', 'Miscellaneous', 'Contingency']

function openDetails(row) {
  detailsRow.value = row
  detailsOpen.value = true
}

function saveDetails({ row_key, values }) {
  send(focusVersion.value.name, [{ op: 'update', row_key, values }])
}
</script>
