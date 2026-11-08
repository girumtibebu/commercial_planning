import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from commercial_planning.api import planning as planning_api
from commercial_planning.api import version as version_api
from commercial_planning.tests.test_conversions import sales_order_from, submitted_quotation

VERSION = "Commercial Planning Version"
PLAN = "Commercial Planning"


def make_project(order=None, name="Planning test project"):
	company = frappe.get_all("Company", pluck="name", limit=1)[0]
	data = {"doctype": "Project", "project_name": name, "company": company}
	if order:
		data.update({"sales_order": order.name, "customer": order.customer})
	return frappe.get_doc(data).insert()


class TestProjects(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def planned_order(self):
		quotation = submitted_quotation()
		plan = planning_api.open_for("Quotation", quotation.name)
		order = sales_order_from(quotation)
		return plan, order

	def test_project_adds_a_budget_version_that_becomes_budget_on_approval(self):
		plan, order = self.planned_order()
		project = make_project(order)
		plan_doc = frappe.get_doc(PLAN, plan)
		self.assertEqual((plan_doc.project, plan_doc.current_stage), (project.name, "Project"))
		so_version, budget = (frappe.get_doc(VERSION, f"{plan}-V0{n}") for n in (2, 3))
		self.assertEqual((so_version.status, budget.status), ("Frozen", "Working"))
		self.assertEqual((budget.stage, budget.purpose, budget.template, budget.created_from_version), ("Project", "Budget", "Project Budget", so_version.name))
		self.assertEqual((budget.source_doctype, budget.source_name), ("Sales Order", order.name))  # selling still comes from the order
		self.assertEqual(flt(budget.total_selling), flt(order.net_total))
		self.assertFalse(budget.reference_role)  # a budget needs Management approval first
		version_api.approve(budget.name)
		plan_doc = frappe.get_doc(PLAN, plan)
		self.assertEqual((plan_doc.budget_version, plan_doc.current_stage), (budget.name, "Execution"))
		self.assertEqual(planning_api.open_for("Project", project.name), plan)

	def test_project_without_a_sales_order_starts_an_empty_plan(self):
		project = make_project(name="Standalone project")
		plan = planning_api.open_for("Project", project.name)
		plan_doc = frappe.get_doc(PLAN, plan)
		version = frappe.get_doc(VERSION, f"{plan}-V01")
		self.assertEqual((plan_doc.created_from, plan_doc.project), ("Project", project.name))
		self.assertEqual((version.stage, version.purpose, len(version.items)), ("Project", "Budget", 0))

	def test_a_second_project_is_not_attached(self):
		plan, order = self.planned_order()
		first = make_project(order, "First")
		make_project(order, "Second")
		self.assertEqual(frappe.db.get_value(PLAN, plan, "project"), first.name)
		self.assertEqual(frappe.db.count(VERSION, {"planning": plan}), 3)
