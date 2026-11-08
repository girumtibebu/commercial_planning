<template>
  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Details</h1>
      <p class="text-xs text-ink-gray-5">Assignments, attachments, tags and sharing — the same as on the standard form.</p>
    </div>

    <div v-if="!details" class="p-10 text-center text-sm text-ink-gray-5">Loading…</div>

    <div v-else class="grid gap-4 lg:grid-cols-2">
      <!-- Record -->
      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
        <h2 class="mb-3 text-sm font-semibold text-ink-gray-9">Record</h2>
        <dl class="grid grid-cols-[120px_1fr] gap-y-2 text-sm">
          <dt class="text-ink-gray-5">Plan</dt>
          <dd class="font-mono text-xs text-ink-gray-8">{{ planName }}</dd>
          <dt class="text-ink-gray-5">Created by</dt>
          <dd>{{ details.created.by_full_name }} · <span class="text-ink-gray-5" :title="fullDate(details.created.on)">{{ timeAgo(details.created.on) }}</span></dd>
          <dt class="text-ink-gray-5">Last edited by</dt>
          <dd>{{ details.modified.by_full_name }} · <span class="text-ink-gray-5" :title="fullDate(details.modified.on)">{{ timeAgo(details.modified.on) }}</span></dd>
          <dt class="text-ink-gray-5">Stage</dt>
          <dd><Badge :label="ws.plan.current_stage" theme="blue" size="sm" /> <Badge :label="ws.plan.status" theme="gray" size="sm" /></dd>
          <dt class="text-ink-gray-5">Linked</dt>
          <dd class="flex flex-col gap-1">
            <a v-for="doc in details.linked" :key="doc.name" :href="deskPath(doc.doctype, doc.name)" class="text-ink-blue-6 hover:underline">
              {{ doc.doctype }} {{ doc.name }} <span v-if="doc.status" class="text-ink-gray-5">· {{ doc.status }}</span>
            </a>
            <span v-if="!details.linked.length" class="text-ink-gray-5">Nothing linked yet.</span>
          </dd>
        </dl>
      </section>

      <!-- Assigned to -->
      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
        <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold text-ink-gray-9"><Icon name="user" :size="14" /> Assigned to</h2>
        <ul class="mb-3 flex flex-col gap-1.5">
          <li v-for="person in details.assignees" :key="person.name" class="flex items-center gap-2 rounded-md bg-surface-gray-1 px-2.5 py-1.5 text-sm">
            <Avatar :label="person.full_name" size="sm" />
            <span class="flex-1 truncate">{{ person.full_name }}</span>
            <button v-if="details.can.write" class="text-ink-gray-4 hover:text-ink-red-6" title="Remove" @click="run(() => api.unassign(planName, person.allocated_to))">
              <Icon name="close" :size="12" />
            </button>
          </li>
          <li v-if="!details.assignees.length" class="text-sm text-ink-gray-5">Not assigned to anyone.</li>
        </ul>
        <LinkField v-if="details.can.write" v-model="assignee" label="Assign to" doctype="User" placeholder="Search a user…" />
      </section>

      <!-- Tags -->
      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
        <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold text-ink-gray-9"><Icon name="tag" :size="14" /> Tags</h2>
        <div class="mb-3 flex flex-wrap gap-1.5">
          <span v-for="tag in details.tags" :key="tag" class="inline-flex items-center gap-1 rounded-full bg-surface-gray-2 px-2.5 py-0.5 text-xs text-ink-gray-8">
            {{ tag }}
            <button v-if="details.can.write" class="text-ink-gray-5 hover:text-ink-red-6" @click="run(() => api.removeTag(planName, tag))"><Icon name="close" :size="10" /></button>
          </span>
          <span v-if="!details.tags.length" class="text-sm text-ink-gray-5">No tags.</span>
        </div>
        <form v-if="details.can.write" class="flex gap-2" @submit.prevent="addTag">
          <input v-model="tag" class="h-8 flex-1 rounded-md border border-outline-gray-3 px-2.5 text-sm outline-none focus:border-outline-blue-3" placeholder="Add a tag…" />
          <Button type="submit" :disabled="!tag.trim()">Add</Button>
        </form>
      </section>

      <!-- Shared with -->
      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
        <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold text-ink-gray-9"><Icon name="share" :size="14" /> Shared with</h2>
        <ul class="mb-3 flex flex-col gap-1.5">
          <li v-for="person in details.shared" :key="person.user" class="flex items-center gap-2 rounded-md bg-surface-gray-1 px-2.5 py-1.5 text-sm">
            <Avatar :label="person.full_name" size="sm" />
            <span class="flex-1 truncate">{{ person.full_name }}</span>
            <Badge :label="person.write ? 'Can edit' : 'Can view'" theme="gray" size="sm" />
            <button v-if="details.can.share" class="text-ink-gray-4 hover:text-ink-red-6" title="Stop sharing" @click="run(() => api.unshare(planName, person.user))">
              <Icon name="close" :size="12" />
            </button>
          </li>
          <li v-if="!details.shared.length" class="text-sm text-ink-gray-5">Not shared with anyone.</li>
        </ul>
        <div v-if="details.can.share" class="flex items-end gap-2">
          <div class="flex-1"><LinkField v-model="shareUser" label="Share with" doctype="User" placeholder="Search a user…" /></div>
          <label class="flex h-8 items-center gap-1.5 text-sm text-ink-gray-7"><input v-model="shareWrite" type="checkbox" /> Can edit</label>
        </div>
      </section>

      <!-- Attachments -->
      <section class="rounded-lg border border-outline-gray-2 bg-surface-white p-4 lg:col-span-2">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="flex items-center gap-2 text-sm font-semibold text-ink-gray-9"><Icon name="paperclip" :size="14" /> Attachments</h2>
          <Button v-if="details.can.write" size="sm" :loading="uploading" @click="picker.click()">
            <template #prefix><Icon name="plus" :size="12" /></template>
            Attach a file
          </Button>
          <input ref="picker" type="file" class="hidden" @change="upload" />
        </div>
        <ul class="flex flex-col divide-y divide-outline-gray-1">
          <li v-for="file in details.attachments" :key="file.name" class="flex items-center gap-3 py-2 text-sm">
            <Icon name="paperclip" :size="13" class="text-ink-gray-5" />
            <a :href="file.file_url" target="_blank" class="flex-1 truncate text-ink-blue-6 hover:underline">{{ file.file_name }}</a>
            <span class="text-xs text-ink-gray-5">{{ file.owner_full_name }} · {{ timeAgo(file.creation) }}</span>
            <Badge v-if="file.is_private" label="Private" theme="gray" size="sm" />
            <button v-if="details.can.write" class="text-ink-gray-4 hover:text-ink-red-6" title="Remove" @click="removeFile(file)">
              <Icon name="trash" :size="13" />
            </button>
          </li>
          <li v-if="!details.attachments.length" class="py-2 text-sm text-ink-gray-5">No attachments.</li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup>
import { inject, onMounted, ref, watch } from 'vue'
import { Avatar, Badge, Button, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import LinkField from '../components/LinkField.vue'
import { api } from '../api'
import { fullDate, timeAgo } from '../format'
import { readError } from '../useWorkspace'

const { ws, planName, deskPath } = inject('cp')

const details = ref(null)
const assignee = ref('')
const shareUser = ref('')
const shareWrite = ref(false)
const tag = ref('')
const picker = ref(null)
const uploading = ref(false)

async function run(request) {
  try {
    details.value = await request()
  } catch (err) {
    toast.error(readError(err))
  }
}

const load = () => run(() => api.getDetails(planName))

watch(assignee, (user) => {
  if (!user) return
  run(() => api.assign(planName, user))
  assignee.value = ''
})

watch(shareUser, (user) => {
  if (!user) return
  run(() => api.shareWith(planName, user, shareWrite.value))
  shareUser.value = ''
})

async function addTag() {
  const value = tag.value.trim()
  if (!value) return
  tag.value = ''
  await run(() => api.addTag(planName, value))
}

async function upload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  uploading.value = true
  try {
    await api.upload(planName, file)
    await load()
  } catch (err) {
    toast.error(readError(err))
  } finally {
    uploading.value = false
  }
}

function removeFile(file) {
  if (window.confirm(`Remove ${file.file_name}?`)) run(() => api.removeAttachment(planName, file.name))
}

onMounted(load)
</script>
