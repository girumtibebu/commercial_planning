<template>
  <Dialog v-model="open" :options="{ title: 'New version', size: 'lg' }">
    <template #body-content>
      <div class="grid gap-3 text-sm">
        <label class="grid gap-1">
          <span class="text-ink-gray-6">Template (optional)</span>
          <select v-model="template" class="h-8 rounded border border-outline-gray-3 bg-surface-white px-2" @change="applyTemplate">
            <option value="">None — set everything below</option>
            <option v-for="tpl in templates" :key="tpl.name" :value="tpl.name">{{ tpl.name }} ({{ tpl.stage }} · {{ tpl.purpose }})</option>
          </select>
        </label>
        <p v-if="selected" class="rounded bg-surface-gray-2 px-2 py-1 text-xs text-ink-gray-7">{{ rules }}</p>

        <label class="grid gap-1">
          <span class="text-ink-gray-6">Create from</span>
          <select v-model="from" class="h-8 rounded border border-outline-gray-3 bg-surface-white px-2">
            <option v-for="ver in versions" :key="ver.name" :value="ver.name">
              V{{ ver.version_no }} {{ ver.version_name }} · {{ ver.status }}
            </option>
          </select>
        </label>

        <label class="grid gap-1">
          <span class="text-ink-gray-6">Name</span>
          <input v-model="name" class="h-8 rounded border border-outline-gray-3 px-2" placeholder="e.g. Vendor Revision, Cost Optimization" />
        </label>

        <div class="grid grid-cols-2 gap-3">
          <label class="grid gap-1">
            <span class="text-ink-gray-6">Stage</span>
            <select v-model="stage" class="h-8 rounded border border-outline-gray-3 bg-surface-white px-2">
              <option v-for="item in stages" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-ink-gray-6">Purpose</span>
            <select v-model="purpose" class="h-8 rounded border border-outline-gray-3 bg-surface-white px-2">
              <option v-for="item in purposes" :key="item" :value="item">{{ item }}</option>
            </select>
          </label>
        </div>

        <label class="flex items-start gap-2">
          <input v-model="apply" type="checkbox" class="mt-0.5" />
          <span>
            <span class="text-ink-gray-8">Bring in the changes from the document</span>
            <span class="block text-xs text-ink-gray-5">
              New items, quantity, unit and selling price are updated from {{ sourceName || 'the document' }}. Lines you edited keep your values.
            </span>
          </span>
        </label>

        <label class="grid gap-1">
          <span class="text-ink-gray-6">Reason <span class="text-ink-red-6">*</span></span>
          <textarea v-model="reason" rows="2" class="rounded border border-outline-gray-3 p-2" placeholder="Why is this version needed?" />
        </label>

        <div class="mt-1 flex justify-end gap-2">
          <Button label="Cancel" @click="open = false" />
          <Button variant="solid" label="Create version" :disabled="!ready" :loading="busy" @click="submit" />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button, Dialog } from 'frappe-ui'

const props = defineProps({
  modelValue: Boolean,
  versions: Array,
  templates: Array,
  stages: Array,
  purposes: Array,
  defaultFrom: String,
  preset: String,
  applyChanges: Boolean,
})
const emit = defineEmits(['update:modelValue', 'create'])

const open = computed({ get: () => props.modelValue, set: (value) => emit('update:modelValue', value) })

const template = ref('')
const from = ref('')
const name = ref('')
const stage = ref('')
const purpose = ref('')
const reason = ref('')
const busy = ref(false)
const apply = ref(false)
const sourceName = computed(() => props.versions.find((ver) => ver.name === from.value)?.source_name)

const selected = computed(() => props.templates.find((tpl) => tpl.name === template.value))
const ready = computed(() => from.value && name.value.trim() && stage.value && purpose.value && reason.value.trim())

const rules = computed(() => {
  const tpl = selected.value
  if (!tpl) return ''
  const parts = [`Copies from: ${tpl.copy_from}.`]
  if (tpl.freeze_source) parts.push('The version it is copied from will be frozen.')
  if (tpl.requires_approval) parts.push('Freezing needs Commercial Management approval.')
  if (tpl.reference_role) parts.push(`Becomes the ${tpl.reference_role} version${tpl.reference_role === 'Budget' ? ' once approved' : ''}.`)
  return parts.join(' ')
})

function applyTemplate() {
  const tpl = selected.value
  if (!tpl) return
  name.value = tpl.version_name || tpl.name
  stage.value = tpl.stage
  purpose.value = tpl.purpose
}

watch(open, (value) => {
  if (!value) return
  template.value = ''
  from.value = props.preset || props.defaultFrom || props.versions[props.versions.length - 1]?.name
  const source = props.versions.find((ver) => ver.name === from.value)
  apply.value = props.applyChanges
  name.value = props.applyChanges && source ? `${source.version_name} (updated)` : ''
  stage.value = source?.stage || props.stages[0]
  purpose.value = 'Revision'
  reason.value = props.applyChanges && source?.source_name ? `${source.source_name} changed` : ''
})

async function submit() {
  busy.value = true
  const created = await new Promise((resolve) =>
    emit('create', {
      from_version: from.value,
      template: template.value || undefined,
      version_name: name.value.trim(),
      stage: stage.value,
      purpose: purpose.value,
      reason: reason.value.trim(),
      apply_source_changes: apply.value ? 1 : 0,
      done: resolve,
    }),
  )
  busy.value = false
  if (created) open.value = false
}
</script>
