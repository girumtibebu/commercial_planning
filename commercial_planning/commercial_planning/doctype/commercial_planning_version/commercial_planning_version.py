import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from commercial_planning.services import selling, tree
from commercial_planning.services import version as version_service

FROZEN = ("Frozen", "Approved")


class CommercialPlanningVersion(Document):
	def autoname(self):
		self.name = f"{self.planning}-V{self.version_no:02d}"

	def before_insert(self):
		self.version_no = version_service.next_version_no(self.planning)
		plan = frappe.db.get_value("Commercial Planning", self.planning, ["currency", "company"], as_dict=True)
		self.currency, self.company = plan.currency, plan.company

	def validate(self):
		self.guard_frozen()
		self.require_reason()
		selling.validate_links(self)
		self.compute()

	def on_update(self):
		version_service.refresh_pointers(self.planning)

	def on_trash(self):
		if self.status in FROZEN:
			frappe.throw(_("A frozen or approved version cannot be deleted"))

	def after_delete(self):
		version_service.refresh_pointers(self.planning)

	def guard_frozen(self):
		if self.is_new() or self.flags.allow_frozen_write:
			return
		if self.get_db_value("status") in FROZEN:
			frappe.throw(_("{0} is frozen and cannot be changed").format(self.name), frappe.ValidationError)

	def require_reason(self):
		if (self.version_no or 1) > 1 and not (self.reason or "").strip():
			frappe.throw(_("A reason is required for this version"))

	def compute(self):
		if self.is_new():
			selling.refresh_selling(self)
		else:
			selling.refresh_totals(self)  # selling is re-read only on request, never silently
		tree.recalculate(self)
		self.total_profit = flt(self.total_selling) - flt(self.total_cost)
		self.margin_pct = self.total_profit / self.total_selling * 100 if flt(self.total_selling) else 0
