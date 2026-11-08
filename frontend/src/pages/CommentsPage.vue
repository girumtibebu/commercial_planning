<template>
  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-5">
    <div>
      <h1 class="text-lg font-semibold text-ink-gray-9">Comments</h1>
      <p class="text-xs text-ink-gray-5">Discuss this plan with your team. Comments are kept with the record.</p>
    </div>

    <div class="rounded-lg border border-outline-gray-2 bg-surface-white p-4">
      <textarea
        v-model="draft"
        rows="3"
        class="w-full rounded-md border border-outline-gray-3 p-2.5 text-sm outline-none focus:border-outline-blue-3"
        placeholder="Write a comment… (Ctrl+Enter to post)"
        @keydown.ctrl.enter.prevent="post"
        @keydown.meta.enter.prevent="post"
      />
      <div class="mt-2 flex justify-end">
        <Button variant="solid" :loading="posting" :disabled="!draft.trim()" @click="post">Comment</Button>
      </div>
    </div>

    <div v-if="loading" class="p-6 text-center text-sm text-ink-gray-5">Loading…</div>
    <div v-else-if="!comments.length" class="rounded-lg border border-dashed border-outline-gray-3 p-8 text-center text-sm text-ink-gray-5">
      No comments yet. Start the conversation above.
    </div>

    <ul v-else class="flex flex-col gap-3">
      <li v-for="comment in comments" :key="comment.name" class="flex gap-3">
        <Avatar :label="comment.owner_full_name" size="md" />
        <div class="min-w-0 flex-1 rounded-lg border border-outline-gray-2 bg-surface-white px-4 py-3">
          <div class="flex items-center gap-2 text-sm">
            <span class="font-semibold text-ink-gray-9">{{ comment.owner_full_name }}</span>
            <span class="text-xs text-ink-gray-5" :title="fullDate(comment.creation)">{{ timeAgo(comment.creation) }}</span>
            <button
              v-if="comment.mine"
              class="ml-auto text-ink-gray-4 hover:text-ink-red-6"
              title="Delete comment"
              @click="remove(comment.name)"
            >
              <Icon name="trash" :size="13" />
            </button>
          </div>
          <div class="mt-1 text-sm text-ink-gray-8" v-html="comment.content" />
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { inject, onMounted, ref } from 'vue'
import { Avatar, Button, toast } from 'frappe-ui'
import Icon from '../components/Icon.vue'
import { api } from '../api'
import { fullDate, timeAgo } from '../format'
import { readError } from '../useWorkspace'

const { planName } = inject('cp')

const comments = ref([])
const draft = ref('')
const loading = ref(true)
const posting = ref(false)

async function load() {
  try {
    comments.value = await api.getComments(planName)
  } catch (err) {
    toast.error(readError(err))
  } finally {
    loading.value = false
  }
}

async function post() {
  if (!draft.value.trim()) return
  posting.value = true
  try {
    comments.value = await api.addComment(planName, draft.value)
    draft.value = ''
  } catch (err) {
    toast.error(readError(err))
  } finally {
    posting.value = false
  }
}

async function remove(name) {
  if (!window.confirm('Delete this comment?')) return
  try {
    comments.value = await api.deleteComment(planName, name)
  } catch (err) {
    toast.error(readError(err))
  }
}

onMounted(load)
</script>
