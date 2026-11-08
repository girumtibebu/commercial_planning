import frappe
from frappe import _

from commercial_planning.services import permissions

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in to open Commercial Planning"), frappe.PermissionError)
	permissions.require(permissions.can_view_plans(), _("You do not have access to Commercial Planning"))
	frappe.db.commit()
	context.boot = frappe._dict(
		{
			"csrf_token": frappe.sessions.get_csrf_token(),
			"site_name": frappe.local.site,
			"frappe_version": frappe.__version__,
			"user": frappe.session.user,
			"user_fullname": frappe.utils.get_fullname(),
		}
	)
	return context
