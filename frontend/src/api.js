import { call } from 'frappe-ui'

const PREFIX = 'commercial_planning.api.'

const json = (value) => (value == null ? undefined : JSON.stringify(value))

export const api = {
  getWorkspace: (plan, versions) =>
    call(PREFIX + 'planning.get_workspace', { plan, versions: json(versions) }),

  applyOps: (version, ops, expectedModified, versions) =>
    call(PREFIX + 'planning.apply_ops', {
      version,
      ops: JSON.stringify(ops),
      expected_modified: expectedModified,
      versions: json(versions),
    }),

  createVersion: (args, versions) =>
    call(PREFIX + 'version.create', { ...args, versions: json(versions) }),

  freeze: (version, versions) => call(PREFIX + 'version.freeze', { version, versions: json(versions) }),

  approve: (version, versions) => call(PREFIX + 'version.approve', { version, versions: json(versions) }),

  reopen: (version, reason, versions) =>
    call(PREFIX + 'version.reopen', { version, reason, versions: json(versions) }),

  setRole: (version, role, versions) =>
    call(PREFIX + 'version.set_role', { version, role: role || '', versions: json(versions) }),

  logView: (plan) => call(PREFIX + 'activity.log_view', { plan }),
  getActivity: (plan, version) => call(PREFIX + 'activity.get_activity', { plan, version: version || undefined }),
  getComments: (plan) => call(PREFIX + 'activity.get_comments', { plan }),
  addComment: (plan, content) => call(PREFIX + 'activity.add_comment', { plan, content }),
  deleteComment: (plan, comment) => call(PREFIX + 'activity.delete_comment', { plan, comment }),

  getDetails: (plan) => call(PREFIX + 'details.get_details', { plan }),
  assign: (plan, user) => call(PREFIX + 'details.assign', { plan, user }),
  unassign: (plan, user) => call(PREFIX + 'details.unassign', { plan, user }),
  addTag: (plan, tag) => call(PREFIX + 'details.add_tag', { plan, tag }),
  removeTag: (plan, tag) => call(PREFIX + 'details.remove_tag', { plan, tag }),
  shareWith: (plan, user, write) => call(PREFIX + 'details.share_with', { plan, user, write: write ? 1 : 0 }),
  unshare: (plan, user) => call(PREFIX + 'details.unshare', { plan, user }),
  removeAttachment: (plan, file) => call(PREFIX + 'details.remove_attachment', { plan, file }),

  async upload(plan, file) {
    const form = new FormData()
    form.append('file', file, file.name)
    form.append('is_private', '1')
    form.append('doctype', 'Commercial Planning')
    form.append('docname', plan)
    form.append('folder', 'Home/Attachments')
    const response = await fetch('/api/method/upload_file', {
      method: 'POST',
      body: form,
      credentials: 'include',
      headers: { 'X-Frappe-CSRF-Token': window.csrf_token },
    })
    if (!response.ok) throw new Error(`Upload failed (${response.status})`)
    return (await response.json()).message
  },

  getItemName: (item) =>
    call('frappe.client.get_value', { doctype: 'Item', fieldname: 'item_name', filters: item }).then((r) => r?.item_name),

  searchLink: (doctype, txt) =>
    call('frappe.desk.search.search_link', { doctype, txt: txt || '', page_length: 10 }),
}

export const deskUrl = (doctype, name) =>
  `/desk/${doctype.toLowerCase().replace(/ /g, '-')}/${encodeURIComponent(name)}`
