import json

import frappe
from frappe import _

from commercial_planning.services import permissions, sync, tree, workspace
from commercial_planning.services import version as version_service

PLAN = "Commercial Planning"
VERSION = "Commercial Planning Version"


def parse_list(value):
	return json.loads(value) if isinstance(value, str) else value


@frappe.whitelist()
def can_open():
	return permissions.can_view_plans()


@frappe.whitelist()
def open_for(doctype, name):
	"""Return the plan a Quotation or Sales Order belongs to, creating or linking it on first use."""
	permissions.require(permissions.can_view_plans(), _("You do not have access to Commercial Planning"))
	frappe.has_permission(doctype, "read", doc=name, throw=True)
	if doctype not in ("Quotation", "Sales Order", "Project"):
		frappe.throw(_("Commercial Planning for {0} is not available yet").format(doctype))
	plan = version_service.get_plan_for(doctype, name)
	if plan:
		frappe.has_permission(PLAN, "read", doc=plan, throw=True)
		return plan
	frappe.has_permission(PLAN, "create", throw=True)
	if doctype == "Sales Order":
		plan = version_service.link_sales_order(name)
	elif doctype == "Project":
		plan = version_service.link_project(name)
	else:
		plan = version_service.create_plan_from_quotation(name)
	if not plan:
		frappe.throw(_("{0} could not be connected to a Commercial Planning record").format(name))
	return plan


@frappe.whitelist()
def sync_summary(doctype, name):
	"""For a document form: is its plan in sync with the document's items?"""
	if not permissions.can_view_plans():
		return None
	frappe.has_permission(doctype, "read", doc=name, throw=True)
	return sync.sync_summary(doctype, name)


@frappe.whitelist()
def get_workspace(plan, versions=None):
	return workspace.get_workspace(plan, parse_list(versions))


@frappe.whitelist()
def apply_ops(version, ops, expected_modified=None, versions=None):
	"""Apply row operations atomically to one Working version and return the refreshed workspace."""
	doc = frappe.get_doc(VERSION, version)
	permissions.require_edit(doc)
	if expected_modified and str(doc.modified) != str(expected_modified):
		frappe.throw(_("This version was changed by someone else. Reload and try again."), frappe.TimestampMismatchError)
	created = tree.apply_ops(doc, parse_list(ops) or [])
	doc.save(ignore_version=False)  # row edits feed the activity log, also under the test runner
	return {"created": created, "workspace": workspace.get_workspace(doc.planning, parse_list(versions))}
