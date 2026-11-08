"""Document events: keep plans connected to the documents they follow. Never block the document."""

import frappe

from commercial_planning.services import version as version_service


def guarded(action):
	"""Run `action`; on failure log it instead of breaking Quotation / Sales Order saving (raise in tests)."""
	try:
		action()
	except Exception:
		if frappe.flags.in_test:
			raise
		frappe.log_error(title="Commercial Planning could not follow a document")


def sales_order_created(doc, method=None):
	guarded(lambda: version_service.link_sales_order(doc.name))


def project_created(doc, method=None):
	guarded(lambda: version_service.link_project(doc.name))


def quotation_created(doc, method=None):
	if doc.amended_from:
		guarded(lambda: version_service.follow_amendment(doc.name))
