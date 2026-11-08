<template>
  <div
    ref="gridEl"
    class="sheet relative h-full overflow-auto bg-surface-white text-sm text-ink-gray-8 outline-none"
    tabindex="0"
    @keydown="onGridKey"
    @mouseleave="hoverKey = null"
  >
    <div class="grid w-max min-w-full" :style="{ gridTemplateColumns }">
      <!-- group bands -->
      <div
        v-for="(group, index) in groups"
        :key="'g' + index"
        class="sheet-head sticky top-0 z-10 flex h-7 items-center px-3 text-[10px] font-semibold uppercase tracking-widest"
        :class="[group.tone, index === 0 ? 'sheet-frozen z-20' : '']"
        :style="{ gridColumn: `span ${group.span}` }"
      >
        {{ group.label }}
      </div>

      <!-- column headers -->
      <div
        v-for="(col, index) in cols"
        :key="'h' + col.key"
        class="sheet-head sticky z-10 flex h-8 items-center gap-1.5 bg-surface-gray-1 px-3 text-[11px] font-medium uppercase tracking-wide text-ink-gray-5"
        :class="[col.number ? 'justify-end' : '', index === 0 ? 'sheet-frozen z-20' : '']"
        :style="{ top: '28px' }"
      >
        <template v-if="col.version">
          <span :class="col.version === focusName ? 'text-ink-blue-8' : ''">{{ col.label }}</span>
          <span v-if="col.role" class="rounded bg-surface-blue-2 px-1 text-[9px] normal-case text-ink-blue-8">{{ col.role }}</span>
        </template>
        <template v-else>{{ col.label }}</template>
      </div>

      <!-- rows -->
      <template v-for="row in rows" :key="row.row_key">
        <div
          v-for="(col, index) in cols"
          :key="row.row_key + col.key"
          :data-cell="row.row_key + ':' + col.key"
          class="sheet-cell"
          :class="cellClasses(row, col, index)"
          @mousedown="col.key !== 'actions' && onCellMouseDown(row, col)"
          @dblclick="col.key !== 'actions' && beginEdit(row, col)"
          @mouseenter="hoverKey = row.row_key"
        >
          <template v-if="col.key === 'actions'">
            <div v-if="canEdit" class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100" :class="{ '!opacity-100': hoverKey === row.row_key || active.key === row.row_key }">
              <Dropdown :options="rowMenu(row)" placement="right">
                <button class="flex h-6 w-6 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-3" title="Row actions">
                  <Icon name="dots" :size="14" />
                </button>
              </Dropdown>
              <button class="flex h-6 w-6 items-center justify-center rounded text-ink-gray-5 hover:bg-surface-red-2 hover:text-ink-red-6" title="Delete row" @click="act(row, remove)">
                <Icon name="close" :size="12" />
              </button>
            </div>
          </template>

          <template v-else-if="isEditing(row, col)">
            <LinkInput
              v-if="typeOf(row, col) === 'link'"
              :doctype="doctypeOf(row, col)"
              :initial="draft"
              :keep-caret="typedStart"
              @commit="(value) => commitLink(row, col, value)"
              @cancel="cancelEdit"
            />
            <input
              v-else
              ref="editor"
              v-model="draft"
              :inputmode="col.type === 'number' ? 'decimal' : 'text'"
              @keydown="onEditKey($event, row, col)"
              @blur="onEditBlur(row, col)"
            />
          </template>

          <template v-else-if="index === 0">
            <span
              class="mr-1 flex h-5 w-5 shrink-0 cursor-pointer select-none items-center justify-center rounded text-ink-gray-5 hover:bg-surface-gray-3"
              :style="{ marginLeft: row.depth * 18 + 'px' }"
              @mousedown.stop.prevent="row.hasChildren && toggle(row.row_key)"
            >
              <Icon v-if="row.hasChildren" :name="collapsed.has(row.row_key) ? 'chevright' : 'chevdown'" :size="12" />
            </span>
            <span v-if="!row.description" class="truncate italic text-ink-gray-4">
              {{ row.row_type === 'Category' ? 'Untitled category' : 'New cost line' }}
            </span>
            <span v-else class="truncate">{{ row.description }}</span>
            <span
              v-if="valuesIn(row, focusName)?.cost_type && row.row_type !== 'Category'"
              class="ml-2 shrink-0 rounded-full bg-surface-gray-2 px-2 py-px text-[10px] font-medium text-ink-gray-6"
            >{{ valuesIn(row, focusName).cost_type }}</span>
            <span v-if="valuesIn(row, focusName)?.supplier" class="ml-2 truncate text-xs text-ink-gray-5">{{ valuesIn(row, focusName).supplier }}</span>
            <Icon v-if="valuesIn(row, focusName)?.notes" name="message" :size="11" class="ml-2 shrink-0 text-ink-gray-4" :title="valuesIn(row, focusName).notes" />
            <span
              v-if="changeFlag(row)"
              class="ml-2 shrink-0 rounded px-1 text-[9px] font-semibold uppercase tracking-wide"
              :class="changeFlag(row) === 'new' ? 'bg-surface-green-2 text-ink-green-8' : 'bg-surface-amber-2 text-ink-amber-8'"
            >{{ changeFlag(row) }}</span>
          </template>

          <template v-else>
            <span class="truncate">{{ display(row, col) }}</span>
          </template>
        </div>
      </template>

      <!-- totals -->
      <div
        v-for="(col, index) in cols"
        :key="'t' + col.key"
        class="sheet-head sticky bottom-0 z-10 flex h-9 items-center border-t border-outline-gray-2 bg-surface-gray-1 px-3 text-sm font-semibold text-ink-gray-9"
        :class="[col.number ? 'justify-end' : '', index === 0 ? 'sheet-frozen z-20' : '']"
      >
        {{ totalFor(col) }}
      </div>
    </div>

    <div v-if="!rows.length" class="flex flex-col items-center gap-2 p-10 text-center text-ink-gray-5">
      <span>{{ filtering ? 'No rows match the filter.' : 'No rows yet.' }}</span>
      <Button v-if="canEdit && !filtering" size="sm" @click="addCategory">Add a category to start planning</Button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Button, Dropdown, toast } from 'frappe-ui'
import Icon from './Icon.vue'
import LinkInput from './LinkInput.vue'
import { api } from '../api'
import { parseNumber } from '../format'
import { indexRows, moveOp, visibleRows } from '../tree'

const props = defineProps({
  ws: { type: Object, required: true },
  focus: { type: Object, default: null },
  fmt: { type: Object, required: true },
  send: { type: Function, required: true },
  search: { type: String, default: '' },
  costType: { type: String, default: '' },
})
const emit = defineEmits(['details'])

const gridEl = ref(null)
const editor = ref(null)
const collapsed = ref(new Set())
const active = ref({ key: null, col: 'description' })
const editing = ref(false)
const draft = ref('')
const typedStart = ref(false)
const hoverKey = ref(null)

const filtering = computed(() => Boolean(props.search || props.costType))
const focusName = computed(() => props.focus?.name)
const canEdit = computed(() => Boolean(props.focus?.can_edit))

/* ------------------------------------------------------------------ columns */
const BANDS = {
  line: { label: 'Plan line', tone: 'bg-surface-gray-2 text-ink-gray-6' },
  cost: { label: 'Internal cost', tone: 'bg-surface-amber-2 text-ink-amber-8' },
  selling: { label: 'Client selling', tone: 'bg-surface-blue-2 text-ink-blue-8' },
  result: { label: 'Result', tone: 'bg-surface-green-2 text-ink-green-8' },
  none: { label: '', tone: 'bg-surface-white' },
}

const cols = computed(() => {
  const versions = props.ws.columns
  const costs = versions.map((column) => ({
    key: 'cost:' + column.version,
    label: column.short,
    role: column.role,
    version: column.version,
    width: 124,
    type: 'readonly',
    number: true,
    band: 'cost',
  }))
  return [
    { key: 'description', label: 'Description', width: 380, type: 'text', band: 'line' },
    { key: 'qty', label: 'Qty', width: 78, type: 'number', number: true, field: 'qty', band: 'line' },
    { key: 'uom', label: 'UOM', width: 88, type: 'link', doctype: 'UOM', field: 'uom', band: 'line' },
    { key: 'unit_cost', label: 'Unit cost', width: 112, type: 'number', number: true, field: 'unit_cost', band: 'line' },
    ...costs,
    ...(costs.length > 1 ? [{ key: 'delta', label: 'Δ vs first', width: 112, type: 'readonly', number: true, band: 'cost' }] : []),
    { key: 'actual', label: 'Actual', width: 110, type: 'readonly', number: true, band: 'cost' },
    { key: 'selling', label: 'Selling', width: 124, type: 'readonly', number: true, band: 'selling' },
    { key: 'profit', label: 'Profit', width: 116, type: 'readonly', number: true, band: 'result' },
    { key: 'margin', label: 'Margin', width: 84, type: 'readonly', number: true, band: 'result' },
    { key: 'actions', label: '', width: 64, type: 'readonly', band: 'none' },
  ]
})

const groups = computed(() => {
  const merged = []
  for (const col of cols.value) {
    const last = merged[merged.length - 1]
    if (last && last.band === col.band) last.span += 1
    else merged.push({ band: col.band, span: 1 })
  }
  return merged.map((group) => ({ ...group, label: BANDS[group.band].label, tone: BANDS[group.band].tone }))
})

const gridTemplateColumns = computed(() =>
  cols.value.map((col, i) => (i === cols.value.length - 2 ? `minmax(${col.width}px, 1fr)` : col.width + 'px')).join(' '),
)

/* --------------------------------------------------------------------- rows */
const index = computed(() => indexRows(props.ws.rows))

function matchText(row, search, costType) {
  const holders = Object.values(row.values)
  if (costType && !holders.some((v) => v.cost_type === costType)) return false
  if (!search) return true
  const needle = search.toLowerCase()
  const haystack = [row.description, ...holders.flatMap((v) => [v.supplier, v.item_code, v.cost_type, v.notes])]
  return haystack.some((text) => text && String(text).toLowerCase().includes(needle))
}

const rows = computed(() =>
  visibleRows(props.ws.rows, { collapsed: collapsed.value, search: props.search, costType: props.costType, matchText }),
)

const activeRow = computed(() => index.value.byKey.get(active.value.key) || null)

function toggle(key) {
  const next = new Set(collapsed.value)
  next.has(key) ? next.delete(key) : next.add(key)
  collapsed.value = next
}

function setAllCollapsed(value) {
  collapsed.value = new Set(value ? props.ws.rows.filter((r) => r.row_type === 'Category').map((r) => r.row_key) : [])
}

/* ------------------------------------------------------------------ values */
const latestVersion = computed(() => props.ws.columns[props.ws.columns.length - 1]?.version)

const valuesIn = (row, version) => row.values[version] || null

function fieldFor(row, col) {
  if (col.field === 'unit_cost' && row.row_type === 'Adjustment' && valuesIn(row, focusName.value)?.adj_mode !== 'Fixed') {
    return 'adj_percent'
  }
  return col.field
}

function rawValue(row, col) {
  if (col.key === 'description') return row.description
  return valuesIn(row, focusName.value)?.[fieldFor(row, col)]
}

const sellingOf = (row) => valuesIn(row, latestVersion.value)?.selling_amount || null
const costOf = (row, version) => valuesIn(row, version)?.cost_amount ?? null

function profitOf(row) {
  const selling = sellingOf(row)
  const cost = costOf(row, latestVersion.value)
  return selling == null || cost == null ? null : selling - cost
}

function deltaOf(row) {
  const columns = props.ws.columns
  const first = costOf(row, columns[0].version)
  const last = costOf(row, columns[columns.length - 1].version)
  return first == null || last == null ? null : last - first
}

/** 'new' / 'changed' marker: how this row differs from the version shown before the focus version. */
function changeFlag(row) {
  const columns = props.ws.columns
  const at = columns.findIndex((column) => column.version === focusName.value)
  if (at < 1) return null
  const before = valuesIn(row, columns[at - 1].version)
  const now = valuesIn(row, focusName.value)
  if (now && !before) return 'new'
  if (now && before && Math.abs((now.cost_amount || 0) - (before.cost_amount || 0)) > 0.005) return 'changed'
  return null
}

function display(row, col) {
  const fmt = props.fmt
  if (col.key === 'qty' || col.key === 'uom' || col.key === 'unit_cost') {
    const values = valuesIn(row, focusName.value)
    if (!values) return '—'
    const field = fieldFor(row, col)
    const value = values[field]
    if (field === 'adj_percent') return `${value || 0}%`
    if (col.number) return value ? fmt.number(value) : ''
    return value ?? ''
  }
  if (col.key.startsWith('cost:')) return costOf(row, col.version) == null ? '—' : fmt.number(costOf(row, col.version))
  if (col.key === 'delta') return deltaOf(row) == null ? '' : fmt.signed(deltaOf(row))
  if (col.key === 'actual') return fmt.number(props.ws.actuals.rows[row.row_key]?.Actual) || ''
  if (col.key === 'selling') return fmt.number(sellingOf(row)) || ''
  if (col.key === 'profit') return profitOf(row) == null ? '' : fmt.number(profitOf(row))
  if (col.key === 'margin') {
    const selling = sellingOf(row)
    return selling && profitOf(row) != null ? fmt.percent((profitOf(row) / selling) * 100) : ''
  }
  return ''
}

function totalFor(col) {
  const fmt = props.fmt
  const latest = props.ws.versions.find((v) => v.name === latestVersion.value)
  if (col.key === 'description') return 'Total'
  if (col.key === 'selling') return fmt.number(latest?.total_selling)
  if (col.key.startsWith('cost:')) return fmt.number(props.ws.versions.find((v) => v.name === col.version)?.total_cost)
  if (col.key === 'delta') {
    const totals = props.ws.columns.map((c) => props.ws.versions.find((v) => v.name === c.version)?.total_cost)
    return fmt.signed(totals[totals.length - 1] - totals[0])
  }
  if (col.key === 'actual') return fmt.number(props.ws.summary.costs.actual) || ''
  if (col.key === 'profit') return fmt.number(latest?.total_profit)
  if (col.key === 'margin') return fmt.percent(latest?.margin_pct)
  return ''
}

/* ----------------------------------------------------------------- classes */
function isEditable(row, col) {
  if (!canEdit.value || col.type === 'readonly') return false
  if (!valuesIn(row, focusName.value)) return false
  if (row.row_type === 'Category' && ['qty', 'uom', 'unit_cost'].includes(col.key)) return false
  if (row.row_type === 'Adjustment' && ['qty', 'uom'].includes(col.key)) return false
  return true
}

function cellClasses(row, col, colIndex) {
  const isActive = active.value.key === row.row_key && active.value.col === col.key
  const profit = col.key === 'profit' || col.key === 'margin' ? profitOf(row) : null
  const editable = isEditable(row, col)
  return [
    col.number ? 'is-number justify-end' : '',
    isActive ? 'is-active' : '',
    colIndex === 0 ? 'sheet-frozen' : '',
    colIndex === 0 && active.value.key === row.row_key ? 'is-row-active' : '',
    hoverKey.value === row.row_key ? 'bg-surface-gray-1' : row.row_type === 'Category' ? (row.parent_key ? 'bg-surface-gray-1' : 'bg-surface-gray-2') : 'bg-surface-white',
    row.row_type === 'Category' ? 'font-semibold text-ink-gray-9' : '',
    row.row_type === 'Adjustment' ? 'italic text-ink-gray-6' : '',
    col.key.startsWith('cost:') && col.version !== focusName.value ? 'text-ink-gray-6' : '',
    !editable && ['qty', 'uom', 'unit_cost'].includes(col.key) ? 'text-ink-gray-6' : '',
    profit != null && profit < 0 ? '!text-ink-red-6' : '',
    profit != null && profit > 0 ? 'text-ink-green-6' : '',
    col.key === 'delta' && deltaOf(row) > 0 ? '!text-ink-red-6' : '',
    col.key === 'delta' && deltaOf(row) < 0 ? 'text-ink-green-6' : '',
    col.key === 'actions' ? 'group' : '',
  ]
}

/* ----------------------------------------------------------------- editing */
/** Category names come from the Item master (like a Desk Link field); other descriptions are free text. */
const typeOf = (row, col) => (col.key === 'description' && row.row_type === 'Category' ? 'link' : col.type)
const doctypeOf = (row, col) => (col.key === 'description' ? 'Item' : col.doctype)

const isEditing = (row, col) => editing.value && active.value.key === row.row_key && active.value.col === col.key

function select(key, colKey) {
  active.value = { key, col: colKey }
  nextTick(scrollActiveIntoView)
}

function scrollActiveIntoView() {
  const cell = gridEl.value?.querySelector(`[data-cell="${CSS.escape(active.value.key + ':' + active.value.col)}"]`)
  cell?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}

function onCellMouseDown(row, col) {
  if (editing.value) return
  const same = active.value.key === row.row_key && active.value.col === col.key
  select(row.row_key, col.key)
  if (same && isEditable(row, col)) beginEdit(row, col)
}

async function beginEdit(row, col, initial) {
  if (!isEditable(row, col)) return
  select(row.row_key, col.key)
  const current = rawValue(row, col)
  draft.value = initial ?? (current == null || current === 0 ? '' : String(current))
  typedStart.value = initial != null
  editing.value = true
  if (typeOf(row, col) !== 'link') {
    await nextTick()
    const input = Array.isArray(editor.value) ? editor.value[0] : editor.value
    input?.focus()
    initial == null ? input?.select() : input?.setSelectionRange(draft.value.length, draft.value.length)
  }
}

function cancelEdit() {
  editing.value = false
  gridEl.value?.focus()
}

function finishEdit() {
  editing.value = false
  gridEl.value?.focus()
}

function onEditBlur(row, col) {
  if (editing.value) commitText(row, col, draft.value, null)
}

function onEditKey(event, row, col) {
  event.stopPropagation()
  if (event.key === 'Escape') {
    event.preventDefault()
    cancelEdit()
  } else if (event.key === 'Enter') {
    event.preventDefault()
    commitText(row, col, draft.value, event.shiftKey ? 'up' : 'down')
  } else if (event.key === 'Tab') {
    event.preventDefault()
    commitText(row, col, draft.value, event.shiftKey ? 'left' : 'right')
  }
}

async function commitLink(row, col, value) {
  if (!editing.value) return
  if (col.key !== 'description') return commitText(row, col, value, 'down')
  finishEdit()
  if (!value) return
  const values = { item_code: value }
  values.description = (await api.getItemName(value)) || value
  const source = index.value.byKey.get(row.row_key) || row
  source.description = values.description
  const own = valuesIn(source, focusName.value)
  if (own) own.item_code = values.item_code
  props.send(focusName.value, [{ op: 'update', row_key: row.row_key, values }])
  moveActive('down')
}

function commitText(row, col, text, move) {
  if (!editing.value) return
  const field = col.key === 'description' ? 'description' : fieldFor(row, col)
  let value = text
  if (col.type === 'number') {
    value = text.trim() === '' ? 0 : parseNumber(text)
    if (value == null) {
      toast.error(`"${text}" is not a number`)
      return cancelEdit()
    }
  }
  finishEdit()
  const previous = col.key === 'description' ? row.description : valuesIn(row, focusName.value)?.[field]
  if ((previous ?? '') !== value && !(previous == null && value === 0)) {
    applyLocally(row, col, field, value)
    props.send(focusName.value, [{ op: 'update', row_key: row.row_key, values: { [field]: value } }])
  }
  if (move) moveActive(move)
}

function applyLocally(row, col, field, value) {
  const source = index.value.byKey.get(row.row_key) || row
  if (col.key === 'description') source.description = value
  const values = valuesIn(source, focusName.value)
  if (values) values[field] = value
}

/* -------------------------------------------------------------- navigation */
const NAV_COLS = computed(() => cols.value.filter((col) => col.key !== 'actions'))

function moveActive(direction) {
  const list = rows.value
  const keys = NAV_COLS.value
  const at = list.findIndex((r) => r.row_key === active.value.key)
  const colAt = keys.findIndex((c) => c.key === active.value.col)
  if (direction === 'down' && at < list.length - 1) select(list[at + 1].row_key, active.value.col)
  else if (direction === 'up' && at > 0) select(list[at - 1].row_key, active.value.col)
  else if (direction === 'right') {
    if (colAt < keys.length - 1) select(active.value.key, keys[colAt + 1].key)
    else if (at < list.length - 1) select(list[at + 1].row_key, keys[0].key)
  } else if (direction === 'left') {
    if (colAt > 0) select(active.value.key, keys[colAt - 1].key)
    else if (at > 0) select(list[at - 1].row_key, keys[keys.length - 1].key)
  }
}

function onGridKey(event) {
  if (editing.value) return
  const row = rows.value.find((r) => r.row_key === active.value.key) || null
  const col = cols.value.find((c) => c.key === active.value.col)
  if (!row) {
    if (rows.value.length && ['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) {
      event.preventDefault()
      select(rows.value[0].row_key, 'description')
    }
    return
  }
  const mod = event.ctrlKey || event.metaKey
  if (event.altKey && handleRowShortcut(event)) return
  if (mod && event.key === 'Enter') return stop(event, () => addLine())
  if (mod && event.key.toLowerCase() === 'd') return stop(event, () => duplicate())
  if (mod && event.key === 'Delete') return stop(event, () => remove())
  if (event.shiftKey && event.key === 'Enter') return stop(event, () => emit('details', row))
  switch (event.key) {
    case 'ArrowDown': return stop(event, () => moveActive('down'))
    case 'ArrowUp': return stop(event, () => moveActive('up'))
    case 'ArrowRight':
      if (col.key === 'description' && row.hasChildren && collapsed.value.has(row.row_key)) return stop(event, () => toggle(row.row_key))
      return stop(event, () => moveActive('right'))
    case 'ArrowLeft':
      if (col.key === 'description' && row.hasChildren && !collapsed.value.has(row.row_key)) return stop(event, () => toggle(row.row_key))
      return stop(event, () => moveActive('left'))
    case 'Tab': return stop(event, () => moveActive(event.shiftKey ? 'left' : 'right'))
    case 'Enter':
    case 'F2': return stop(event, () => beginEdit(row, col))
    case 'Delete':
    case 'Backspace':
      return stop(event, () => clearCell(row, col))
    default:
      if (event.key.length === 1 && !mod && !event.altKey) {
        event.preventDefault()
        beginEdit(row, col, typeOf(row, col) === 'link' ? event.key : event.key)
      }
  }
}

function stop(event, action) {
  event.preventDefault()
  action()
}

function handleRowShortcut(event) {
  const actions = { ArrowUp: () => moveRow(-1), ArrowDown: () => moveRow(1), ArrowRight: indent, ArrowLeft: outdent }
  const action = actions[event.key]
  if (!action) return false
  event.preventDefault()
  action()
  return true
}

function clearCell(row, col) {
  if (!isEditable(row, col) || col.key === 'description') return
  editing.value = true
  commitText(row, col, '', null)
}

/* ------------------------------------------------------------ row actions */
function requireRow() {
  if (!canEdit.value) return toast.error('This version is read-only. Pick a Working version to edit.')
  return activeRow.value || null
}

async function addRow(values, { asChild } = {}) {
  if (!canEdit.value) return toast.error('This version is read-only. Pick a Working version to edit.')
  const row = activeRow.value
  const temp = 'tmp' + Date.now()
  let parent_key = ''
  let before_key = null
  if (row) {
    const childMode = asChild ?? row.row_type === 'Category'
    parent_key = childMode ? row.row_key : row.parent_key || ''
    if (!childMode) {
      const siblings = index.value.children.get(parent_key) || []
      before_key = siblings[siblings.indexOf(row.row_key) + 1] || null
    }
  }
  if (parent_key) collapsed.value.delete(parent_key)
  const created = await props.send(focusName.value, [{ op: 'add', temp_id: temp, parent_key, before_key, values }])
  const key = created[temp]
  if (!key) return
  await nextTick()
  select(key, 'description')
  const added = props.ws.rows.find((r) => r.row_key === key)
  if (added) beginEdit({ ...added, hasChildren: false }, cols.value[0])
}

const addLine = () => addRow({ row_type: 'Cost Item' })
const addCategory = () => addRow({ row_type: 'Category' }, { asChild: false })
const addAdjustment = () =>
  addRow({ row_type: 'Adjustment', adj_mode: 'Percent of parent', adj_percent: 0, description: 'Contingency' })

const sendFor = (op) => props.send(focusName.value, [op])

function indent() {
  const row = requireRow()
  if (row) sendFor({ op: 'indent', row_key: row.row_key })
}

function outdent() {
  const row = requireRow()
  if (row) sendFor({ op: 'outdent', row_key: row.row_key })
}

function moveRow(direction) {
  const row = requireRow()
  const op = row && moveOp(row, index.value.children, direction)
  if (op) sendFor(op)
}

function duplicate() {
  const row = requireRow()
  if (row) sendFor({ op: 'duplicate', row_key: row.row_key })
}

function split() {
  const row = requireRow()
  if (row) sendFor({ op: 'split', row_key: row.row_key })
}

function remove() {
  const row = requireRow()
  if (!row) return
  if (row.hasChildren && !window.confirm(`Delete "${row.description}" and everything under it?`)) return
  moveActive('down')
  if (active.value.key === row.row_key) moveActive('up')
  sendFor({ op: 'delete', row_key: row.row_key })
}

/** Run a row action against a specific row (from its hover menu). */
function act(row, action) {
  select(row.row_key, 'description')
  action()
}

function rowMenu(row) {
  const isCategory = row.row_type === 'Category'
  const items = [
    { label: 'Line details…', onClick: () => act(row, () => emit('details', row)) },
    { label: isCategory ? 'Add line inside' : 'Add line below', onClick: () => act(row, addLine) },
  ]
  if (!isCategory) items.push({ label: 'Split into lines', onClick: () => act(row, split) })
  items.push(
    { label: 'Indent', onClick: () => act(row, indent) },
    { label: 'Outdent', onClick: () => act(row, outdent) },
    { label: 'Move up', onClick: () => act(row, () => moveRow(-1)) },
    { label: 'Move down', onClick: () => act(row, () => moveRow(1)) },
    { label: 'Duplicate', onClick: () => act(row, duplicate) },
    { label: 'Delete', theme: 'red', onClick: () => act(row, remove) },
  )
  return items
}

watch(
  () => props.focus?.name,
  () => {
    editing.value = false
  },
)

defineExpose({
  activeRow,
  addLine,
  addCategory,
  addAdjustment,
  setAllCollapsed,
  focus: () => gridEl.value?.focus(),
})
</script>
