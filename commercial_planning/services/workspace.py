"""Read model for the Vue workspace: header, version columns, merged matrix and KPIs."""

import frappe
from frappe.utils import flt

from commercial_planning.services import permissions
from commercial_planning.services import sync as sync_service
from commercial_planning.services import version as version_service

VERSION = "Commercial Planning Version"
IDENTITY = ("row_key", "parent_key", "row_type", "description")
VALUE_FIELDS = (
	"notes",
	"cost_type",
	"cost_source",
	"item_code",
	"supplier",
	"vendor_quote",
	"qty",
	"uom",
	"unit_cost",
	"cost_currency",
	"exchange_rate",
	"adj_mode",
	"adj_percent",
	"cost_amount",
	"selling_amount",
)
VERSION_FIELDS = (
	"name",
	"version_no",
	"version_name",
	"stage",
	"purpose",
	"status",
	"reference_role",
	"template",
	"reason",
	"owner",
	"creation",
	"modified",
	"frozen_by",
	"frozen_on",
	"approved_by",
	"approved_on",
	"created_from_version",
	"source_doctype",
	"source_name",
	"total_selling",
	"total_cost",
	"total_profit",
	"margin_pct",
)
PLAN_FIELDS = (
	"name",
	"title",
	"customer",
	"company",
	"currency",
	"status",
	"current_stage",
	"quotation",
	"sales_order",
	"project",
)


def get_workspace(plan, versions=None):
	doc = frappe.get_doc("Commercial Planning", plan)
	doc.check_permission("read")
	all_versions = frappe.get_all(VERSION, filters={"planning": plan}, fields=list(VERSION_FIELDS), order_by="version_no asc")
	selected = pick_columns(doc, all_versions, versions)
	return {
		"plan": plan_header(doc),
		"versions": [describe_version(ver) for ver in all_versions],
		"columns": [column_for(ver) for ver in selected],
		"rows": merged_rows(selected),
		"actuals": actual_totals(doc, selected),
		"summary": summary(doc, all_versions),
		"sync": sync_status(selected),
		"templates": templates(),
		"stages": frappe.get_all("Commercial Version Stage", pluck="name", order_by="creation asc"),
		"purposes": frappe.get_all("Commercial Version Purpose", pluck="name", order_by="creation asc"),
	}


def templates():
	return frappe.get_all(
		"Commercial Version Template",
		fields=["name", "version_name", "stage", "purpose", "copy_from", "reference_role", "freeze_source", "requires_approval", "trigger"],
		order_by="creation asc",
	)


def sync_status(selected):
	"""Per displayed version: differences from the document it is built on."""
	status = {}
	for ver in selected:
		found = sync_service.get_status(frappe.get_doc(VERSION, ver.name))
		if found:
			status[ver.name] = found
	return status


def pick_columns(doc, all_versions, requested):
	"""Requested versions; else the reference versions (baseline, budget, forecast) plus the latest."""
	by_name = {ver.name: ver for ver in all_versions}
	if requested:
		return [by_name[name] for name in requested if name in by_name]
	pointers = version_service.get_pointers(doc.name)
	names = [pointers["baseline_version"], pointers["budget_version"], pointers["forecast_version"]]
	chosen = {name for name in names if name in by_name}
	if all_versions:
		chosen.add(all_versions[-1].name)
	return sorted((by_name[name] for name in chosen), key=lambda ver: ver.version_no)


LINKED = (("Quotation", "quotation"), ("Sales Order", "sales_order"), ("Project", "project"))


def linked_documents(doc):
	"""The ERPNext documents this plan follows, with their current status."""
	found = []
	for doctype, field in LINKED:
		name = doc.get(field)
		if name:
			found.append({"doctype": doctype, "name": name, "status": frappe.db.get_value(doctype, name, "status")})
	return found


def plan_header(doc):
	header = {field: doc.get(field) for field in PLAN_FIELDS}
	header["can_write"] = bool(frappe.has_permission("Commercial Planning", "write", doc=doc))
	header["linked"] = linked_documents(doc)
	header["owner"] = doc.owner
	return header


def version_label(ver):
	return f"V{ver.version_no} {ver.version_name}"


def describe_version(ver):
	doc = frappe.get_doc(VERSION, ver.name)
	return dict(ver) | {
		"label": version_label(ver),
		"can_edit": permissions.can_edit_version(doc),
		"can_freeze": permissions.can_freeze_version(doc),
		"can_approve": permissions.can_approve_version(doc),
		"can_reopen": permissions.can_reopen_version(doc),
		"can_set_role": {role: permissions.can_set_role(doc, role) for role in version_service.ROLES},
	}


def column_for(ver):
	return {
		"version": ver.name,
		"key": f"v{ver.version_no}",
		"label": version_label(ver),
		"short": f"V{ver.version_no}",
		"role": ver.reference_role,
		"status": ver.status,
	}


def version_rows(name):
	fields = list(IDENTITY + VALUE_FIELDS)
	return frappe.get_all(
		"Commercial Planning Item",
		filters={"parent": name, "parenttype": VERSION},
		fields=fields,
		order_by="idx asc",
	)


def merged_rows(selected):
	"""Union of the rows of every selected version, joined by row_key, in tree order."""
	if not selected:
		return []
	priority = list(reversed(selected))
	per_version = {}
	children = {}
	for ver in priority:
		rows = version_rows(ver.name)
		per_version[ver.name] = {row.row_key: row for row in rows}
		children[ver.name] = {}
		for row in rows:
			children[ver.name].setdefault(row.parent_key or "", []).append(row.row_key)
	output = []
	walk("", 0, priority, per_version, children, output)
	return output


def merge_order(parent_key, priority, children):
	merged = []
	for ver in priority:
		siblings = children[ver.name].get(parent_key, [])
		for index, key in enumerate(siblings):
			if key in merged:
				continue
			previous = siblings[index - 1] if index else None
			if previous in merged:
				merged.insert(merged.index(previous) + 1, key)
			elif index == 0:
				merged.insert(0, key)
			else:
				merged.append(key)
	return merged


def walk(parent_key, depth, priority, per_version, children, output):
	for key in merge_order(parent_key, priority, children):
		holders = [ver for ver in priority if key in per_version[ver.name]]
		first = per_version[holders[0].name][key]
		output.append(
			{
				"row_key": key,
				"parent_key": parent_key,
				"depth": depth,
				"row_type": first.row_type,
				"description": first.description,
				"values": {ver.name: strip_identity(per_version[ver.name][key]) for ver in holders},
			}
		)
		walk(key, depth + 1, priority, per_version, children, output)


def strip_identity(row):
	return {field: row.get(field) for field in VALUE_FIELDS}


def actual_totals(doc, selected):
	"""Actual/committed per row_key rolled up the newest selected tree; plus the unallocated bucket."""
	entries = frappe.db.sql(
		"""select row_key, basis, sum(amount) as amount from `tabCommercial Planning Actual`
		where planning=%s group by row_key, basis""",
		doc.name,
		as_dict=True,
	)
	result = {"rows": {}, "unallocated": {"Actual": 0, "Committed": 0}}
	parents = {}
	if selected:
		for row in version_rows(selected[-1].name):
			parents[row.row_key] = row.parent_key
	for entry in entries:
		key = entry.row_key
		if not key or key not in parents:
			result["unallocated"][entry.basis] += flt(entry.amount)
			continue
		while key:
			bucket = result["rows"].setdefault(key, {"Actual": 0, "Committed": 0})
			bucket[entry.basis] += flt(entry.amount)
			key = parents.get(key)
	return result


def summary(doc, all_versions):
	pointers = version_service.get_pointers(doc.name)
	by_name = {ver.name: ver for ver in all_versions}
	baseline = by_name.get(pointers["baseline_version"])
	budget = by_name.get(pointers["budget_version"])
	forecast = by_name.get(pointers["forecast_version"])
	current = all_versions[-1] if all_versions else None  # selling follows the most recent version
	selling = flt(current.total_selling) if current else 0
	costs = {
		"quotation": flt(baseline.total_cost) if baseline else None,
		"budget": flt(budget.total_cost) if budget else None,
		"forecast": flt(forecast.total_cost) if forecast else None,
		"actual": flt(doc.actual_cost) if doc.actual_cost else None,
	}
	profit = {key: (selling - cost if cost is not None else None) for key, cost in costs.items()}
	margin = {key: (value / selling * 100 if value is not None and selling else None) for key, value in profit.items()}
	return {
		"selling": selling,
		"costs": costs,
		"profit": profit,
		"margin": margin,
		"variance": {
			"budget_vs_quotation": diff(costs["budget"], costs["quotation"]),
			"forecast_vs_budget": diff(costs["forecast"], costs["budget"]),
			"actual_vs_forecast": diff(costs["actual"], costs["forecast"]),
			"actual_vs_quotation": diff(costs["actual"], costs["quotation"]),
		},
	}


def diff(left, right):
	return None if left is None or right is None else left - right
