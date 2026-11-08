"""Activity feed and comments for a plan: who created, opened, changed, commented."""

import json

import frappe
from frappe import _
from frappe.utils import get_datetime

PLAN = "Commercial Planning"
VERSION = "Commercial Planning Version"
ITEM = "Commercial Planning Item"
NOISE = {
	"cost_amount",
	"selling_amount",
	"idx",
	"modified",
	"modified_by",
	"total_cost",
	"total_selling",
	"total_profit",
	"margin_pct",
	"unit_cost_currency",
	"source_rate",
	"parent_key",
	"row_key",
}
VIEW_WINDOW_SECONDS = 30 * 60


def get_plan(plan, ptype="read"):
	doc = frappe.get_doc(PLAN, plan)
	doc.check_permission(ptype)
	return doc


def full_name(user):
	return frappe.db.get_value("User", user, "full_name") or user


def event(kind, key, owner, creation, summary, **extra):
	return {
		"id": f"{kind}:{key}",
		"type": kind,
		"owner": owner,
		"owner_full_name": full_name(owner),
		"creation": str(creation),
		"ts": get_datetime(creation).timestamp(),
		"summary": summary,
		"changes": [],
		**extra,
	}


def label_of(field):
	return (field or "").replace("_", " ")


def shown(value):
	return "—" if value in (None, "") else value


def describe_row_change(row_name, changes):
	name = frappe.db.get_value(ITEM, row_name, "description") or _("a line")
	parts = [f"{label_of(field)} {shown(old)} → {shown(new)}" for field, old, new in changes if field not in NOISE]
	return f"{name}: " + ", ".join(parts) if parts else None


def describe_version_data(data):
	"""Readable change lines from a Frappe Version record (field, row and table changes)."""
	lines = []
	for field, old, new in data.get("changed") or []:
		if field not in NOISE:
			lines.append(f"{label_of(field)} {shown(old)} → {shown(new)}")
	for _table, _idx, row_name, changes in data.get("row_changed") or []:
		line = describe_row_change(row_name, changes)
		if line:
			lines.append(line)
	for table, row in data.get("added") or []:
		if table == "items":
			lines.append(_("Added {0}").format(row.get("description") or _("a line")))
	for table, row in data.get("removed") or []:
		if table == "items":
			lines.append(_("Removed {0}").format(row.get("description") or _("a line")))
	return lines


def version_events(plan, versions, labels, include_plan):
	"""Change events from Frappe's own Version log for the plan and its versions."""
	targets = [(VERSION, [v.name for v in versions])]
	if include_plan:
		targets.append((PLAN, [plan]))
	events = []
	for doctype, names in targets:
		if not names:
			continue
		rows = frappe.get_all(
			"Version",
			filters={"ref_doctype": doctype, "docname": ["in", names]},
			fields=["name", "owner", "creation", "data", "docname"],
			order_by="creation desc",
			limit=200,
		)
		for row in rows:
			try:
				lines = describe_version_data(json.loads(row.data or "{}"))
			except Exception:
				lines = []
			if not lines:
				continue
			where = labels.get(row.docname, _("the plan"))
			count = len(lines)
			summary = lines[0] if count == 1 else _("made {0} changes").format(count)
			events.append(
				event("change", row.name, row.owner, row.creation, summary, version=where, changes=lines)
			)
	return events


def creation_events(versions, labels, wanted):
	events = []
	for ver in versions:
		if ver.name not in wanted:
			continue
		source = f" from {labels[ver.created_from_version]}" if ver.created_from_version in labels else ""
		events.append(
			event("created", ver.name, ver.owner, ver.creation, _("created {0}").format(labels[ver.name]) + source, detail=ver.reason, version=labels[ver.name])
		)
	return events


def comment_events(plan):
	rows = frappe.get_all(
		"Comment",
		filters={"reference_doctype": PLAN, "reference_name": plan, "comment_type": ["in", ["Comment", "Info"]]},
		fields=["name", "owner", "creation", "comment_type", "content"],
		order_by="creation desc",
		limit=100,
	)
	kind = {"Comment": "comment", "Info": "info"}
	return [event(kind[row.comment_type], row.name, row.owner, row.creation, row.content or "", html=True) for row in rows]


def view_events(plan):
	"""Opens of the plan, one per user per half hour."""
	rows = frappe.get_all(
		"View Log",
		filters={"reference_doctype": PLAN, "reference_name": plan},
		fields=["name", "viewed_by", "creation"],
		order_by="creation desc",
		limit=100,
	)
	events, last = [], {}
	for row in rows:
		stamp = get_datetime(row.creation).timestamp()
		if row.viewed_by in last and last[row.viewed_by] - stamp < VIEW_WINDOW_SECONDS:
			continue
		last[row.viewed_by] = stamp
		events.append(event("view", row.name, row.viewed_by, row.creation, _("opened this plan")))
	return events


def assignment_events(plan):
	rows = frappe.get_all(
		"ToDo",
		filters={"reference_type": PLAN, "reference_name": plan},
		fields=["name", "owner", "creation", "status", "allocated_to"],
		order_by="creation desc",
		limit=50,
	)
	return [
		event(
			"assign",
			row.name,
			row.owner,
			row.creation,
			_("closed the assignment of {0}").format(full_name(row.allocated_to or row.owner))
			if row.status == "Closed"
			else _("assigned {0}").format(full_name(row.allocated_to or row.owner)),
		)
		for row in rows
	]


@frappe.whitelist()
def get_activity(plan, version=None, limit=100):
	"""Merged, newest-first activity for a plan; optionally only what touched one version."""
	get_plan(plan)
	versions = frappe.get_all(
		VERSION,
		{"planning": plan},
		["name", "version_no", "version_name", "created_from_version", "reason", "owner", "creation"],
		order_by="version_no asc",
	)
	labels = {ver.name: f"V{ver.version_no} {ver.version_name}" for ver in versions}
	wanted = [version] if version else [ver.name for ver in versions]
	events = creation_events(versions, labels, wanted)
	events += version_events(plan, [ver for ver in versions if ver.name in wanted], labels, include_plan=not version)
	if not version:
		events += comment_events(plan) + view_events(plan) + assignment_events(plan)
	events.sort(key=lambda row: row["ts"], reverse=True)
	return events[: int(limit)]


@frappe.whitelist()
def get_comments(plan):
	get_plan(plan)
	rows = frappe.get_all(
		"Comment",
		filters={"reference_doctype": PLAN, "reference_name": plan, "comment_type": "Comment"},
		fields=["name", "owner", "creation", "content"],
		order_by="creation asc",
	)
	return [
		{**row, "creation": str(row.creation), "owner_full_name": full_name(row.owner), "mine": row.owner == frappe.session.user}
		for row in rows
	]


@frappe.whitelist()
def add_comment(plan, content):
	if not (content or "").strip():
		frappe.throw(_("Write a comment first"))
	doc = get_plan(plan)
	frappe.has_permission(PLAN, "read", doc=doc, throw=True)
	doc.add_comment("Comment", frappe.utils.escape_html(content.strip()).replace("\n", "<br>"))
	return get_comments(plan)


@frappe.whitelist()
def delete_comment(plan, comment):
	get_plan(plan)
	row = frappe.db.get_value("Comment", comment, ["owner", "reference_doctype", "reference_name"], as_dict=True)
	if not row or row.reference_name != plan or row.reference_doctype != PLAN:
		frappe.throw(_("Comment not found"))
	if row.owner != frappe.session.user and not frappe.has_permission(PLAN, "write", doc=plan):
		frappe.throw(_("You can only delete your own comments"), frappe.PermissionError)
	frappe.delete_doc("Comment", comment, ignore_permissions=True)
	return get_comments(plan)


@frappe.whitelist()
def log_view(plan):
	"""Record that the current user opened the plan (shown in the activity feed)."""
	get_plan(plan).add_viewed()
