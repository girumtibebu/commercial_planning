"""Keeps a version aligned with the document items it was built from. Nothing changes silently:
differences are reported, and applied only when the planner asks (add items / refresh)."""

import frappe
from frappe.utils import flt

from commercial_planning.services import selling
from commercial_planning.services import version as version_service

ITEM_DOCTYPE = {"Quotation": "Quotation Item", "Sales Order": "Sales Order Item"}
REVISION = "Commercial Planning Version"
ITEM_FIELDS = ["name", "item_code", "item_name", "qty", "uom", "rate", "net_rate", "net_amount"]
TOLERANCE = 0.005


def source_items(revision):
	"""Live items of the document this revision reads selling from, in document order."""
	doctype = ITEM_DOCTYPE.get(revision.source_doctype)
	if not doctype or not revision.source_name:
		return doctype, []
	filters = {"parent": revision.source_name, "parenttype": revision.source_doctype}
	if frappe.get_meta(doctype).has_field("is_alternative"):
		filters["is_alternative"] = 0
	return doctype, frappe.get_all(doctype, filters=filters, fields=ITEM_FIELDS, order_by="idx asc")


def linked_categories(revision, doctype, live):
	"""{row_key: [category row, [live items it is linked to], live selling]} for linked categories."""
	rows = {row.row_key: row for row in revision.items}
	found = {}
	for link in revision.item_links:
		item = live.get(link.link_name)
		row = rows.get(link.row_key)
		if link.link_doctype != doctype or item is None or row is None:
			continue
		entry = found.setdefault(link.row_key, [row, [], 0.0])
		entry[1].append(item)
		entry[2] += flt(item.net_amount) * flt(link.allocation_pct) / 100
	return found


def describe_changes(row, item, selling_live):
	changes = {}
	if flt(row.qty) != flt(item.qty):
		changes["qty"] = [row.qty, item.qty]
	if (row.uom or "") != (item.uom or ""):
		changes["uom"] = [row.uom, item.uom]
	if abs(flt(row.selling_amount) - selling_live) > TOLERANCE:
		changes["selling"] = [flt(row.selling_amount), selling_live]
	return changes


def get_status(revision):
	"""Differences between the document and the revision: new items, removed items, changed qty/uom/selling."""
	doctype, items = source_items(revision)
	if not doctype:
		return None
	live = {item.name: item for item in items}
	linked_names = {link.link_name for link in revision.item_links if link.link_doctype == doctype}
	by_key = {row.row_key: row for row in revision.items}
	status = {"new_items": [], "removed_items": [], "changes": []}
	for item in items:
		if item.name not in linked_names:
			status["new_items"].append(
				{"name": item.name, "label": item.item_name or item.item_code, "qty": item.qty, "amount": flt(item.net_amount)}
			)
	for link in revision.item_links:
		if link.link_doctype == doctype and link.link_name not in live:
			row = by_key.get(link.row_key)
			status["removed_items"].append(
				{"name": link.link_name, "row_key": link.row_key, "label": row.description if row else ""}
			)
	for row_key, (row, row_items, selling_live) in linked_categories(revision, doctype, live).items():
		changes = describe_changes(row, row_items[0], selling_live)
		if changes:
			status["changes"].append({"row_key": row_key, "label": row.description, **changes})
	status["in_sync"] = not any(status[key] for key in ("new_items", "removed_items", "changes"))
	return status


def add_missing_items(revision, tree_view, only=None):
	"""Add document items not yet in the plan (all, or just `only`)."""
	doctype, items = source_items(revision)
	linked = {link.link_name for link in revision.item_links if link.link_doctype == doctype}
	added = set()
	for item in items:
		if item.name in linked or (only and item.name not in only):
			continue
		category, line = version_service.add_source_item(revision, doctype, item)
		for row in (category, line):
			tree_view.rows[row.row_key] = row
		tree_view.siblings("").append(category)
		tree_view.siblings(category.row_key).append(line)
		added.add(category.row_key)
	selling.refresh_selling(revision, added)


def refresh_rows(revision, tree_view, only=None):
	"""Pull qty, uom and selling from the document. The first line follows only where it was left untouched."""
	doctype, items = source_items(revision)
	live = {item.name: item for item in items}
	touched = set()
	for row_key, (category, row_items, _selling) in linked_categories(revision, doctype, live).items():
		if only and row_key not in only:
			continue
		item = row_items[0]
		follow_first_line(tree_view, category, item)
		category.qty, category.uom = item.qty, item.uom
		category.source_rate = version_service.source_rate(item)
		touched.add(row_key)
	selling.refresh_selling(revision, touched)


def follow_first_line(tree_view, category, item):
	lines = tree_view.siblings(category.row_key)
	first = lines[0] if lines else None
	if not first or first.row_type != "Cost Item":
		return
	if flt(first.qty) == flt(category.qty):
		first.qty = item.qty
	if (first.uom or "") == (category.uom or ""):
		first.uom = item.uom
	if abs(flt(first.unit_cost) - flt(category.source_rate)) <= TOLERANCE:
		first.unit_cost = version_service.source_rate(item)


def sync_summary(doctype, name):
	"""Compact status for a document form: which plan, and what is out of sync."""
	plan = version_service.get_plan_for(doctype, name)
	if not plan:
		return None
	names = frappe.get_all(
		REVISION, {"planning": plan, "source_doctype": doctype, "source_name": name}, pluck="name", order_by="version_no desc"
	)
	if not names:
		return {"plan": plan, "in_sync": True}
	revision = frappe.get_doc(REVISION, names[0])
	status = get_status(revision) or {}
	return {
		"plan": plan,
		"revision": revision.name,
		"working": revision.status == "Working",
		"new_items": status.get("new_items", []),
		"removed_items": status.get("removed_items", []),
		"changes": status.get("changes", []),
		"in_sync": status.get("in_sync", True),
	}
