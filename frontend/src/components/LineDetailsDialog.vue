<template>
  <Dialog v-model="open" :options="{ title: row ? row.description || 'Line details' : 'Line details', size: 'lg' }">
    <template #body-content>
      <div v-if="row" class="grid gap-3 text-sm">
        <label class="grid gap-1">
          <span class="text-ink-gray-6">Description</span>
          <input
            v-model="form.description"
            :disabled="!editable || row.row_type === 'Category'"
            class="h-8 rounded-md border border-outline-gray-3 px-2.5 outline-none focus:border-outline-blue-3 disabled:bg-surface-gray-1"
          />
          <span v-if="row.row_type === 'Category'" class="text-xs text-ink-gray-5">Category names come from the Item master; change them in the grid.</span>
        </label>

        <div class="grid grid-cols-2 gap-3">
          <LinkField v-model="form.cost_type" label="Cost type" doctype="Commercial Cost Type" :disabled="!editable" />
          <LinkField v-model="form.cost_source" label="Cost source" doctype="Commercial Cost Source" :disabled="!editable" />
          <LinkField v-model="form.supplier" label="Supplier" doctype="Supplier" :disabled="!editable" />
          <LinkField v-model="form.item_code" label="ERPNext item (optional)" doctype="Item" :disabled="!editable" />
        </div>

        <label class="grid gap-1">
          <span class="text-ink-gray-6">Notes</span>
          <textarea
            v-model="form.notes"
            rows="3"
            :disabled="!editable"
            class="rounded-md border border-outline-gray-3 p-2.5 outline-none focus:border-outline-blue-3 disabled:bg-surface-gray-1"
            placeholder="Vendor quote reference, assumptions, conditions…"
          />
        </label>

        <div class="mt-1 flex justify-end gap-2">
          <Button label="Close" @click="open = false" />
          <Button v-if="editable" variant="solid" label="Save details" :disabled="!dirty" @click="save" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import LinkField from './LinkField.vue'

const props = defineProps({ modelValue: Boolean, row: Object, version: String, editable: Boolean })
const emit = defineEmits(['update:modelValue', 'save'])

const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })
const FIELDS = ['description', 'cost_type', 'cost_source', 'supplier', 'item_code', 'notes']
const form = reactive({ description: '', cost_type: '', cost_source: '', supplier: '', item_code: '', notes: '' })
let original = {}

watch(
  () => [props.modelValue, props.row],
  () => {
    if (!props.modelValue || !props.row) return
    const values = props.row.values[props.version] || {}
    original = { description: props.row.description || '' }
    for (const field of FIELDS.slice(1)) original[field] = values[field] || ''
    Object.assign(form, original)
  },
  { immediate: true },
)

const changes = computed(() => FIELDS.filter((field) => (form[field] || '') !== (original[field] || '')))
const dirty = computed(() => changes.value.length > 0)

function save() {
  const values = Object.fromEntries(changes.value.map((field) => [field, form[field] || null]))
  emit('save', { row_key: props.row.row_key, values })
  open.value = false
}
</script>
