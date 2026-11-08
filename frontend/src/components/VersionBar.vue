<template>
  <div v-if="focus" class="flex flex-wrap items-center gap-2 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-1.5 text-sm">
    <span class="text-ink-gray-6">{{ focus.can_edit ? 'Editing' : 'Viewing' }}</span>
    <span class="font-semibold text-ink-gray-9">V{{ focus.version_no }} {{ focus.version_name }}</span>
    <Badge :label="focus.status" :theme="focus.status === 'Working' ? 'green' : focus.status === 'Approved' ? 'blue' : 'gray'" />
    <Badge v-if="focus.reference_role" :label="focus.reference_role" theme="blue" />
    <span class="text-xs text-ink-gray-5">{{ focus.stage }} · {{ focus.purpose }}</span>
    <span v-if="focus.reason" class="max-w-[320px] truncate text-ink-gray-6" :title="focus.reason">“{{ focus.reason }}”</span>

    <div class="ml-auto flex items-center gap-2">
      <Button v-if="focus.can_freeze" size="sm" label="Freeze" @click="confirmFreeze = true" />
      <Button v-if="focus.can_approve" size="sm" variant="solid" label="Approve" @click="confirmApprove = true" />
      <Button v-if="focus.can_reopen" size="sm" label="Reopen…" @click="reopenOpen = true" />
    </div>

    <Dialog v-model="confirmFreeze" :options="{ title: 'Freeze version', size: 'md' }">
      <template #body-content>
        <p class="text-sm text-ink-gray-7">
          V{{ focus.version_no }} will become read-only so these numbers are preserved exactly as they are now. Create a new
          version to change them later. Only Commercial Management can reopen it, with a reason.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <Button label="Cancel" @click="confirmFreeze = false" />
          <Button variant="solid" label="Freeze" @click="confirmFreeze = false; act('freeze')" />
        </div>
      </template>
    </Dialog>

    <Dialog v-model="confirmApprove" :options="{ title: 'Approve version', size: 'md' }">
      <template #body-content>
        <p class="text-sm text-ink-gray-7">
          Approving freezes V{{ focus.version_no }}<span v-if="becomesBudget"> and makes it the plan's <b>Budget</b> version</span>.
          It is recorded under your name.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <Button label="Cancel" @click="confirmApprove = false" />
          <Button variant="solid" label="Approve" @click="confirmApprove = false; act('approve')" />
        </div>
      </template>
    </Dialog>

    <Dialog v-model="reopenOpen" :options="{ title: 'Reopen version', size: 'md' }">
      <template #body-content>
        <label class="mb-1 block text-sm text-ink-gray-7">Reason (recorded in the audit trail)</label>
        <textarea v-model="reason" rows="3" class="w-full rounded border border-outline-gray-3 p-2 text-sm" />
        <div class="mt-4 flex justify-end gap-2">
          <Button label="Cancel" @click="reopenOpen = false" />
          <Button variant="solid" label="Reopen" :disabled="!reason.trim()" @click="doReopen" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Badge, Button, Dialog } from 'frappe-ui'

const props = defineProps({ focus: Object, templates: { type: Array, default: () => [] } })
const emit = defineEmits(['freeze', 'approve', 'reopen'])

const confirmFreeze = ref(false)
const confirmApprove = ref(false)
const reopenOpen = ref(false)
const reason = ref('')

const becomesBudget = computed(() => {
  const template = props.templates.find((tpl) => tpl.name === props.focus?.template)
  return template?.reference_role === 'Budget'
})

function act(event) {
  emit(event, props.focus.name)
}

function doReopen() {
  reopenOpen.value = false
  emit('reopen', props.focus.name, reason.value)
  reason.value = ''
}
</script>
