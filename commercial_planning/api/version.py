import frappe

from commercial_planning.api.planning import parse_list
from commercial_planning.services import version as version_service
from commercial_planning.services import workspace

VERSION = "Commercial Planning Version"


def refreshed(planning, versions):
	return workspace.get_workspace(planning, parse_list(versions))


@frappe.whitelist()
def create(
	planning,
	reason,
	from_version=None,
	template=None,
	version_name=None,
	stage=None,
	purpose=None,
	apply_source_changes=0,
	versions=None,
):
	"""Create a version (copy of `from_version`, defaults from `template`) and return the refreshed workspace."""
	new = version_service.create_version(
		planning,
		from_version=from_version,
		template=template,
		version_name=version_name,
		stage=stage,
		purpose=purpose,
		reason=reason,
		apply_source_changes=bool(int(apply_source_changes or 0)),
	)
	shown = (parse_list(versions) or []) + [new.name] if versions else None
	return {"version": new.name, "workspace": refreshed(planning, shown)}


@frappe.whitelist()
def freeze(version, versions=None):
	doc = version_service.freeze(frappe.get_doc(VERSION, version))
	return refreshed(doc.planning, versions)


@frappe.whitelist()
def approve(version, versions=None):
	doc = version_service.approve(frappe.get_doc(VERSION, version))
	return refreshed(doc.planning, versions)


@frappe.whitelist()
def reopen(version, reason, versions=None):
	doc = version_service.reopen(frappe.get_doc(VERSION, version), reason)
	return refreshed(doc.planning, versions)


@frappe.whitelist()
def set_role(version, role=None, versions=None):
	doc = version_service.set_reference_role(frappe.get_doc(VERSION, version), role)
	return refreshed(doc.planning, versions)
