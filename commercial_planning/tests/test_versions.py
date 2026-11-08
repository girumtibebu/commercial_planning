import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from commercial_planning.api import planning as planning_api
from commercial_planning.api import version as version_api
from commercial_planning.tests.test_planning import make_quotation

VERSION = "Commercial Planning Version"


class TestVersions(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.quotation = make_quotation(((1, 1000), (2, 500)))
		self.plan = planning_api.open_for("Quotation", self.quotation.name)
		self.v1 = frappe.get_doc(VERSION, f"{self.plan}-V01")

	def tearDown(self):
		frappe.set_user("Administrator")

	def make(self, **kwargs):
		kwargs.setdefault("reason", "test")
		kwargs.setdefault("from_version", self.v1.name)
		return frappe.get_doc(VERSION, version_api.create(self.plan, **kwargs)["version"])

	def role_holder(self, role):
		return frappe.db.get_value(VERSION, {"planning": self.plan, "reference_role": role}, "name")

	def as_user(self, email, *roles):
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "T", "send_welcome_email": 0, "roles": [{"role": r} for r in roles]}
			).insert()
		frappe.set_user(email)

	def test_first_version_comes_from_the_plan_created_template(self):
		self.assertEqual(
			(
				self.v1.version_no,
				self.v1.version_name,
				self.v1.stage,
				self.v1.purpose,
				self.v1.status,
				self.v1.reference_role,
				self.v1.template,
			),
			(1, "Quotation", "Quotation", "Estimate", "Working", "Baseline", "Quotation"),
		)
		self.assertEqual(frappe.db.get_value("Commercial Planning", self.plan, "baseline_version"), self.v1.name)
		templates = set(frappe.get_all("Commercial Version Template", pluck="name"))
		self.assertTrue({"Quotation", "Sales Order", "Project Budget", "Forecast"} <= templates)

	def test_create_version_copies_the_tree_and_keeps_row_keys(self):
		line = next(row for row in self.v1.items if row.row_type == "Cost Item")
		planning_api.apply_ops(self.v1.name, [{"op": "update", "row_key": line.row_key, "values": {"unit_cost": 777}}])
		v2 = self.make(version_name="Vendor Revision", stage="Quotation", purpose="Revision")
		self.assertEqual((v2.version_no, v2.status, v2.created_from_version), (2, "Working", self.v1.name))
		self.assertFalse(v2.reference_role)
		self.assertEqual([r.row_key for r in v2.items], [r.row_key for r in frappe.get_doc(VERSION, self.v1.name).items])
		planning_api.apply_ops(v2.name, [{"op": "update", "row_key": line.row_key, "values": {"unit_cost": 900}}])
		original = next(r for r in frappe.get_doc(VERSION, self.v1.name).items if r.row_key == line.row_key)
		self.assertEqual(flt(original.unit_cost), 777)  # the source version is untouched
		payload = planning_api.get_workspace(self.plan, [self.v1.name, v2.name])
		self.assertEqual([c["short"] for c in payload["columns"]], ["V1", "V2"])
		moved = next(r for r in payload["rows"] if r["row_key"] == line.row_key)
		self.assertEqual((moved["values"][self.v1.name]["unit_cost"], moved["values"][v2.name]["unit_cost"]), (777, 900))

	def test_a_reason_is_required_for_new_versions(self):
		with self.assertRaises(frappe.ValidationError):
			version_api.create(self.plan, reason=" ", from_version=self.v1.name, version_name="x", stage="Quotation", purpose="Revision")

	def test_freeze_source_template_and_reference_role_uniqueness(self):
		so = self.make(template="Sales Order")
		self.assertEqual((so.stage, so.purpose, so.version_name), ("Sales Order", "Pricing", "Sales Order"))
		self.assertEqual(frappe.db.get_value(VERSION, self.v1.name, "status"), "Frozen")  # source frozen by the template
		first = self.make(template="Forecast", from_version=so.name)
		self.assertEqual(self.role_holder("Forecast"), first.name)
		second = self.make(template="Forecast", from_version=first.name)
		self.assertEqual(self.role_holder("Forecast"), second.name)
		self.assertFalse(frappe.db.get_value(VERSION, first.name, "reference_role"))
		self.assertEqual(frappe.db.get_value("Commercial Planning", self.plan, "forecast_version"), second.name)

	def test_budget_needs_approval_and_clears_when_reopened(self):
		budget = self.make(template="Project Budget")
		self.assertFalse(budget.reference_role)
		with self.assertRaises(frappe.PermissionError):
			version_api.set_role(budget.name, "Budget")  # only an Approved version can become the budget
		version_api.approve(budget.name)
		approved = frappe.get_doc(VERSION, budget.name)
		self.assertEqual((approved.status, approved.reference_role), ("Approved", "Budget"))
		self.assertTrue(approved.approved_by)
		self.assertEqual(frappe.db.get_value("Commercial Planning", self.plan, "budget_version"), budget.name)
		with self.assertRaises(frappe.PermissionError):
			planning_api.apply_ops(budget.name, [{"op": "add", "values": {"description": "late"}}])
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(VERSION, budget.name).save()
		version_api.reopen(budget.name, "price change")
		reopened = frappe.get_doc(VERSION, budget.name)
		self.assertEqual(reopened.status, "Working")
		self.assertFalse(reopened.reference_role or reopened.approved_by)
		self.assertFalse(frappe.db.get_value("Commercial Planning", self.plan, "budget_version"))

	def test_summary_uses_reference_versions(self):
		lines = [row for row in self.v1.items if row.row_type == "Cost Item"]
		planning_api.apply_ops(
			self.v1.name, [{"op": "update", "row_key": row.row_key, "values": {"unit_cost": 100}} for row in lines]
		)
		baseline_cost = flt(frappe.db.get_value(VERSION, self.v1.name, "total_cost"))
		forecast = self.make(template="Forecast")
		planning_api.apply_ops(forecast.name, [{"op": "update", "row_key": lines[0].row_key, "values": {"unit_cost": 150}}])
		payload = planning_api.get_workspace(self.plan)
		self.assertEqual([c["short"] for c in payload["columns"]], ["V1", "V2"])  # baseline + forecast references
		costs = payload["summary"]["costs"]
		self.assertEqual((costs["quotation"], costs["forecast"], costs["budget"]), (baseline_cost, baseline_cost + 50, None))
		self.assertIsNone(payload["summary"]["variance"]["forecast_vs_budget"])

	def test_editors_follow_the_version_template(self):
		forecast = self.make(template="Forecast")
		self.as_user("pm.only@example.com", "Projects Manager")
		versions = {v["name"]: v for v in planning_api.get_workspace(self.plan)["versions"]}
		self.assertTrue(versions[forecast.name]["can_edit"])  # Forecast: planner + projects manager
		self.assertFalse(versions[self.v1.name]["can_edit"])  # Quotation: planner only
		with self.assertRaises(frappe.PermissionError):
			planning_api.apply_ops(self.v1.name, [{"op": "add", "values": {"description": "x"}}])
		planning_api.apply_ops(forecast.name, [{"op": "add", "values": {"description": "pm line", "unit_cost": 1}}])

	def test_planner_cannot_approve_or_freeze_a_budget(self):
		budget = self.make(template="Project Budget")
		self.as_user("planner.only@example.com", "Commercial Planner")
		with self.assertRaises(frappe.PermissionError):
			version_api.approve(budget.name)
		with self.assertRaises(frappe.PermissionError):
			version_api.freeze(budget.name)  # this template requires Management approval
