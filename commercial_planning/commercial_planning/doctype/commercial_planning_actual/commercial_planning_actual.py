import frappe
from frappe import _
from frappe.model.document import Document


class CommercialPlanningActual(Document):
	def validate(self):
		self.currency = frappe.db.get_value("Commercial Planning", self.planning, "currency")
		if self.row_key and not self.is_known_row():
			frappe.throw(_("Row {0} does not exist in plan {1}").format(self.row_key, self.planning))

	def is_known_row(self):
		return bool(
			frappe.db.exists(
				"Commercial Planning Item",
				{"row_key": self.row_key, "parenttype": "Commercial Planning Version", "parent": ["like", f"{self.planning}-V%"]},
			)
		)
