import { computed, ref, watch } from 'vue'
import { toast } from 'frappe-ui'
import { api } from './api'

/** Loads one plan and serialises its edits: every edit is a batch of row operations sent in order. */
export function useWorkspace(planName) {
  const ws = ref(null)
  const loading = ref(true)
  const error = ref(null)
  const shown = ref(null) // version names displayed as columns (null = server default)
  const focusName = ref(null) // version being edited
  const pending = ref(0)
  const saving = ref(false)
  let chain = Promise.resolve()

  async function load() {
    try {
      ws.value = await api.getWorkspace(planName, shown.value)
      error.value = null
    } catch (err) {
      error.value = readError(err)
    } finally {
      loading.value = false
    }
  }

  const versionByName = (name) => ws.value?.versions.find((ver) => ver.name === name)

  /** Queue operations for one version; resolves with {temp_id: row_key} once saved. */
  function send(version, ops) {
    pending.value += 1
    const task = chain.then(async () => {
      saving.value = true
      try {
        const result = await api.applyOps(version, ops, versionByName(version)?.modified, shown.value)
        ws.value = result.workspace
        return result.created
      } catch (err) {
        toast.error(readError(err))
        await load()
        return {}
      } finally {
        pending.value -= 1
        saving.value = pending.value > 0
      }
    })
    chain = task.catch(() => {})
    return task
  }

  async function run(request) {
    saving.value = true
    try {
      ws.value = await request()
      return true
    } catch (err) {
      toast.error(readError(err))
      return false
    } finally {
      saving.value = false
    }
  }

  const freeze = (version) => run(() => api.freeze(version, shown.value))
  const approve = (version) => run(() => api.approve(version, shown.value))
  const reopen = (version, reason) => run(() => api.reopen(version, reason, shown.value))
  const setRole = (version, role) => run(() => api.setRole(version, role, shown.value))

  /** Create a version, show it next to the ones already displayed, and start editing it. */
  async function createVersion(args) {
    saving.value = true
    try {
      const current = ws.value.columns.map((column) => column.version)
      const result = await api.createVersion({ planning: planName, ...args }, current)
      ws.value = result.workspace
      shown.value = ws.value.columns.map((column) => column.version)
      focusName.value = result.version
      return result.version
    } catch (err) {
      toast.error(readError(err))
      return null
    } finally {
      saving.value = false
    }
  }

  async function showVersions(names) {
    const order = new Map(ws.value.versions.map((ver) => [ver.name, ver.version_no]))
    shown.value = [...names].sort((a, b) => order.get(a) - order.get(b))
    await load()
  }

  /** Display or hide one version as a comparison column (at least one stays visible). */
  async function toggleColumn(name) {
    const current = ws.value.columns.map((column) => column.version)
    const next = current.includes(name) ? current.filter((n) => n !== name) : [...current, name]
    if (!next.length) return
    if (focusName.value === name && !next.includes(name)) focusName.value = null
    await showVersions(next)
  }

  async function focusOn(name) {
    focusName.value = name
    if (!ws.value.columns.some((column) => column.version === name)) {
      await showVersions([...ws.value.columns.map((column) => column.version), name])
    }
  }

  /** The version being edited: the chosen one, else the newest editable column, else the last column. */
  const focusVersion = computed(() => {
    if (!ws.value) return null
    const columns = ws.value.columns.map((column) => versionByName(column.version))
    const chosen = columns.find((ver) => ver?.name === focusName.value)
    if (chosen) return chosen
    return [...columns].reverse().find((ver) => ver?.can_edit) || columns[columns.length - 1] || null
  })

  const dirty = computed(() => pending.value > 0 || saving.value)
  watch(dirty, (value) => window.parent?.postMessage({ type: 'cp:dirty', dirty: value }, window.location.origin))

  return {
    ws,
    loading,
    error,
    saving,
    dirty,
    load,
    send,
    freeze,
    approve,
    reopen,
    setRole,
    createVersion,
    toggleColumn,
    focusOn,
    focusVersion,
    versionByName,
  }
}

export function readError(err) {
  const raw = err?.messages?.[0] || err?.message || String(err)
  return String(raw).replace(/<[^>]+>/g, '').slice(0, 300)
}
