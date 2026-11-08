import frappe
from frappe import _
from frappe.model.document import Document

from commercial_planning.services import version as version_service


class CommercialPlanning(Document):
	def validate(self):
		self.current_stage = version_service.derive_stage(self)

	def on_trash(self):
		if frappe.db.exists("Commercial Planning Version", {"planning": self.name, "status": ["in", ["Frozen", "Approved"]]}):
			frappe.throw(_("A plan with frozen versions cannot be deleted; set its status to Cancelled instead"))
		for version in frappe.get_all("Commercial Planning Version", {"planning": self.name}, pluck="name"):
			frappe.delete_doc("Commercial Planning Version", version, force=True)
		for doctype in ("Commercial Planning Actual", "Commercial Vendor Quote"):
			frappe.db.delete(doctype, {"planning": self.name})
