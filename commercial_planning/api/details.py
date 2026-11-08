"""Standard form details for a plan: assignments, attachments, tags, sharing and record info."""

import frappe
from frappe import _
from frappe.desk.doctype.tag import tag as tag_api
from frappe.desk.form import assign_to
from frappe import share

from commercial_planning.api.activity import full_name, get_plan
from commercial_planning.services.workspace import linked_documents

PLAN = "Commercial Planning"


def user_tags(doc):
	if not frappe.db.has_column(PLAN, "_user_tags"):
		return []
	raw = frappe.db.get_value(PLAN, doc.name, "_user_tags") or ""
	return [tag for tag in raw.split(",") if tag]


def get_details_data(plan):
	doc = get_plan(plan)
	todos = frappe.get_all(
		"ToDo",
		filters={"reference_type": PLAN, "reference_name": plan, "status": "Open"},
		fields=["name", "allocated_to", "description", "owner", "creation"],
	)
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": PLAN, "attached_to_name": plan},
		fields=["name", "file_name", "file_url", "is_private", "file_size", "owner", "creation"],
		order_by="creation desc",
	)
	return {
		"assignees": [{**t, "full_name": full_name(t.allocated_to), "creation": str(t.creation)} for t in todos],
		"attachments": [{**f, "creation": str(f.creation), "owner_full_name": full_name(f.owner)} for f in files],
		"tags": user_tags(doc),
		"shared": [
			{"user": s.user, "full_name": full_name(s.user), "read": s.read, "write": s.write, "share": s.share}
			for s in share.get_users(PLAN, plan)
			if s.user
		],
		"created": {"by": doc.owner, "by_full_name": full_name(doc.owner), "on": str(doc.creation)},
		"modified": {"by": doc.modified_by, "by_full_name": full_name(doc.modified_by), "on": str(doc.modified)},
		"linked": linked_documents(doc),
		"can": {
			"write": bool(frappe.has_permission(PLAN, "write", doc=doc)),
			"share": bool(frappe.has_permission(PLAN, "share", doc=doc)),
		},
	}


@frappe.whitelist()
def get_details(plan):
	return get_details_data(plan)


@frappe.whitelist()
def assign(plan, user):
	get_plan(plan, "write")
	assign_to.add({"doctype": PLAN, "name": plan, "assign_to": [user], "description": _("Review commercial plan {0}").format(plan)})
	return get_details_data(plan)


@frappe.whitelist()
def unassign(plan, user):
	get_plan(plan, "write")
	assign_to.remove(PLAN, plan, user)
	return get_details_data(plan)


@frappe.whitelist()
def add_tag(plan, tag):
	get_plan(plan, "write")
	tag_api.add_tag(tag.strip(), PLAN, plan)
	return get_details_data(plan)


@frappe.whitelist()
def remove_tag(plan, tag):
	get_plan(plan, "write")
	tag_api.remove_tag(tag, PLAN, plan)
	return get_details_data(plan)


@frappe.whitelist()
def share_with(plan, user, write=0):
	get_plan(plan, "share")
	share.add(PLAN, plan, user, read=1, write=int(write), share=0, flags={"ignore_share_permission": True})
	return get_details_data(plan)


@frappe.whitelist()
def unshare(plan, user):
	get_plan(plan, "share")
	share.remove(PLAN, plan, user, flags={"ignore_share_permission": True})
	return get_details_data(plan)


@frappe.whitelist()
def remove_attachment(plan, file):
	get_plan(plan, "write")
	attached = frappe.db.get_value("File", file, ["attached_to_doctype", "attached_to_name"], as_dict=True)
	if not attached or (attached.attached_to_doctype, attached.attached_to_name) != (PLAN, plan):
		frappe.throw(_("That file is not attached to this plan"))
	frappe.delete_doc("File", file)
	return get_details_data(plan)
