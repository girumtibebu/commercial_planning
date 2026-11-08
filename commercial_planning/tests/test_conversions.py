import frappe
from erpnext.selling.doctype.quotation.quotation import make_sales_order
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate

from commercial_planning.api import planning as planning_api
from commercial_planning.api import version as version_api
from commercial_planning.tests.test_planning import make_quotation

VERSION = "Commercial Planning Version"
PLAN = "Commercial Planning"


def submitted_quotation(rates=((1, 1000), (2, 500))):
	quotation = make_quotation(rates)
	quotation.submit()
	return quotation


def sales_order_from(quotation, qty=None):
	order = make_sales_order(quotation.name)
	order.delivery_date = add_days(nowdate(), 10)
	for item in order.items:
		item.delivery_date = order.delivery_date
	if qty:
		order.items[0].qty = qty
	return order.insert()


class TestConversions(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def planned_quotation(self, rates=((1, 1000), (2, 500))):
		quotation = submitted_quotation(rates)
		plan = planning_api.open_for("Quotation", quotation.name)
		return quotation, plan, frappe.get_doc(VERSION, f"{plan}-V01")

	def set_first_line_costs(self, version, cost):
		lines = [row for row in version.items if row.row_type == "Cost Item"]
		planning_api.apply_ops(version.name, [{"op": "update", "row_key": r.row_key, "values": {"unit_cost": cost}} for r in lines])

	def test_sales_order_adds_a_version_and_freezes_the_quotation_version(self):
		quotation, plan, v1 = self.planned_quotation()
		self.set_first_line_costs(v1, 700)
		order = sales_order_from(quotation, qty=3)
		plan_doc = frappe.get_doc(PLAN, plan)
		self.assertEqual((plan_doc.sales_order, plan_doc.current_stage), (order.name, "Sales Order"))
		v1, v2 = (frappe.get_doc(VERSION, f"{plan}-V0{n}") for n in (1, 2))
		self.assertEqual((v1.status, v2.status), ("Frozen", "Working"))
		self.assertEqual((v2.stage, v2.purpose, v2.template, v2.created_from_version), ("Sales Order", "Pricing", "Sales Order", v1.name))
		self.assertEqual((v2.source_doctype, v2.source_name), ("Sales Order", order.name))
		self.assertEqual({link.link_doctype for link in v2.item_links}, {"Sales Order Item"})
		self.assertEqual(flt(v2.total_selling), flt(order.net_total))
		category = next(row for row in v2.items if row.row_type == "Category")
		line = next(row for row in v2.items if row.parent_key == category.row_key)
		self.assertEqual((flt(category.qty), flt(line.qty), flt(line.unit_cost)), (3, 3, 700))  # qty follows, edited cost is kept
		self.assertEqual(flt(v1.total_selling), 2000)  # the quotation version keeps what was quoted
		self.assertEqual(planning_api.open_for("Sales Order", order.name), plan)

	def test_sales_order_without_a_quotation_starts_its_own_plan(self):
		source = submitted_quotation()
		order = make_sales_order(source.name)
		for item in order.items:
			item.prevdoc_docname = None
			item.quotation_item = None
			item.delivery_date = add_days(nowdate(), 10)
		order.delivery_date = add_days(nowdate(), 10)
		order.insert()
		plan = planning_api.open_for("Sales Order", order.name)
		version = frappe.get_doc(VERSION, f"{plan}-V01")
		self.assertEqual((version.stage, version.reference_role, version.source_name), ("Sales Order", "Baseline", order.name))
		self.assertEqual(frappe.db.get_value(PLAN, plan, "created_from"), "Sales Order")
		self.assertEqual(flt(version.total_selling), flt(order.net_total))

	def test_a_second_sales_order_is_not_attached(self):
		quotation, plan, _v1 = self.planned_quotation()
		first = sales_order_from(quotation)
		second = sales_order_from(quotation)
		self.assertEqual(frappe.db.get_value(PLAN, plan, "sales_order"), first.name)
		self.assertEqual(frappe.db.count(VERSION, {"planning": plan}), 2)
		self.assertIsNone(frappe.db.get_value(PLAN, {"sales_order": second.name}))

	def test_amended_quotation_is_followed(self):
		quotation, plan, v1 = self.planned_quotation()
		self.set_first_line_costs(v1, 400)
		quotation.reload()
		quotation.cancel()
		amended = frappe.copy_doc(quotation)
		amended.docstatus = 0
		amended.amended_from = quotation.name
		amended.items[0].qty = 2
		amended.insert()
		plan_doc = frappe.get_doc(PLAN, plan)
		self.assertEqual(plan_doc.quotation, amended.name)
		v1, v2 = (frappe.get_doc(VERSION, f"{plan}-V0{n}") for n in (1, 2))
		self.assertEqual((v1.status, v2.status, v2.source_name, v2.purpose), ("Frozen", "Working", amended.name, "Revision"))
		self.assertEqual({link.link_name for link in v2.item_links}, {item.name for item in amended.items})
		self.assertEqual(flt(v2.total_selling), flt(amended.net_total))
		category = next(row for row in v2.items if row.row_type == "Category")
		self.assertEqual(flt(category.qty), 2)
		self.assertEqual(planning_api.open_for("Quotation", amended.name), plan)

	def test_create_version_can_apply_changes_from_the_document(self):
		quotation, plan, _v1 = self.planned_quotation()
		order = sales_order_from(quotation)
		v2 = frappe.get_doc(VERSION, f"{plan}-V02")
		order.items[0].qty = 5
		order.save()
		status = planning_api.get_workspace(plan, [v2.name])["sync"][v2.name]
		self.assertEqual(status["changes"][0]["qty"], [1, 5])
		created = version_api.create(plan, reason="Client changed the order", from_version=v2.name, version_name="Order change", stage="Sales Order", purpose="Revision", apply_source_changes=1)
		v3 = frappe.get_doc(VERSION, created["version"])
		category = next(row for row in v3.items if row.row_type == "Category")
		self.assertEqual((flt(category.qty), flt(v3.total_selling)), (5, flt(order.net_total)))
		self.assertEqual(flt(frappe.db.get_value(VERSION, v2.name, "total_selling")), 1000 + 1000)  # the earlier version is untouched
