"""Version-aware editing rules layered on top of DocType permissions."""

import frappe
from frappe import _

PLANNER = "Commercial Planner"
MANAGEMENT = "Commercial Management"
PROJECTS_MANAGER = "Projects Manager"
ADMIN_ROLES = (MANAGEMENT, "System Manager")
PLAN_ROLES = (PLANNER, MANAGEMENT, PROJECTS_MANAGER, "System Manager")

# Used when a version has no template (ad-hoc versions).
STAGE_EDITORS = {
	"Quotation": (PLANNER,),
	"Sales Order": (PLANNER,),
	"Project": (PLANNER, PROJECTS_MANAGER),
	"Execution": (PLANNER, PROJECTS_MANAGER),
}

EDITABLE_STATUS = "Working"


def has_any_role(roles, user=None):
	return bool(set(frappe.get_roles(user)) & set(roles))


def can_view_plans(user=None):
	return has_any_role(PLAN_ROLES, user)


def editor_roles(version):
	if version.template:
		roles = frappe.get_all(
			"Commercial Template Role", {"parent": version.template, "parenttype": "Commercial Version Template"}, pluck="role"
		)
		if roles:
			return tuple(roles) + ADMIN_ROLES
	return STAGE_EDITORS.get(version.stage, (PLANNER,)) + ADMIN_ROLES


def requires_approval(version):
	return bool(version.template and frappe.db.get_value("Commercial Version Template", version.template, "requires_approval"))


def can_edit_version(version, user=None):
	if version.status != EDITABLE_STATUS:
		return False
	return has_any_role(editor_roles(version), user) and bool(
		frappe.has_permission(version.doctype, "write", doc=version, user=user)
	)


def can_freeze_version(version, user=None):
	if version.status != EDITABLE_STATUS:
		return False
	if requires_approval(version):
		return has_any_role(ADMIN_ROLES, user)
	return can_edit_version(version, user)


def can_approve_version(version, user=None):
	return version.status in (EDITABLE_STATUS, "Frozen") and has_any_role(ADMIN_ROLES, user)


def can_reopen_version(version, user=None):
	return version.status in ("Frozen", "Approved") and has_any_role(ADMIN_ROLES, user)


def can_set_role(version, role, user=None):
	"""Budget needs Management and an Approved version; Baseline/Forecast need an editor of the plan."""
	if role == "Budget":
		return version.status == "Approved" and has_any_role(ADMIN_ROLES, user)
	return has_any_role((PLANNER, PROJECTS_MANAGER) + ADMIN_ROLES, user)


def require(condition, message):
	if not condition:
		frappe.throw(message, frappe.PermissionError)


def require_edit(version):
	require(can_edit_version(version), _("You cannot edit {0}").format(version.name))
