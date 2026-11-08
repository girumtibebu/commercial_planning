import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, nowdate

from commercial_planning.api import planning as planning_api
from commercial_planning.api import version as version_api
from commercial_planning.services import tree

VERSION = "Commercial Planning Version"
REVISION = VERSION


def make_quotation(rates=((1, 850000), (1, 400000), (1, 200000))):
	company = frappe.get_all("Company", pluck="name", limit=1)[0]
	customer = frappe.get_all("Customer", pluck="name", limit=1)[0]
	items = frappe.get_all("Item", filters={"disabled": 0, "is_stock_item": 0}, pluck="name", limit=len(rates)) or frappe.get_all(
		"Item", filters={"disabled": 0}, pluck="name", limit=len(rates)
	)
	quotation = frappe.get_doc(
		{
			"doctype": "Quotation",
			"quotation_to": "Customer",
			"party_name": customer,
			"company": company,
			"transaction_date": nowdate(),
			"valid_till": add_days(nowdate(), 30),
			"items": [
				{"item_code": items[i % len(items)], "qty": qty, "rate": rate} for i, (qty, rate) in enumerate(rates)
			],
		}
	)
	return quotation.insert()


class TestCommercialPlanning(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.quotation = make_quotation()
		self.plan = planning_api.open_for("Quotation", self.quotation.name)
		self.baseline = frappe.get_doc(REVISION, f"{self.plan}-V01")
		self.zero_first_lines()

	def zero_first_lines(self):
		"""First lines start at the quotation rate; most tests want a clean cost slate."""
		lines = [row for row in self.reload().items if row.row_type == "Cost Item"]
		self.ops([{"op": "update", "row_key": row.row_key, "values": {"unit_cost": 0}} for row in lines])

	def reload(self):
		self.baseline = frappe.get_doc(REVISION, self.baseline.name)
		return self.baseline

	def categories(self):
		return [row for row in self.reload().items if row.row_type == "Category"]

	def ops(self, ops):
		return planning_api.apply_ops(self.baseline.name, ops)

	def test_open_for_is_idempotent_and_imports_items(self):
		self.assertEqual(planning_api.open_for("Quotation", self.quotation.name), self.plan)
		self.assertEqual(frappe.db.count(REVISION, {"planning": self.plan}), 1)
		self.assertEqual(len(self.categories()), 3)
		self.assertEqual(len(self.baseline.items), 6)  # every category has a first line
		self.assertEqual(flt(self.baseline.total_selling), 1450000)
		self.assertEqual(flt(self.baseline.total_cost), 0)
		self.assertEqual(len(self.baseline.item_links), 3)

	def test_rollups_profit_and_margin(self):
		led = self.categories()[0].row_key
		result = self.ops(
			[
				{"op": "add", "parent_key": led, "temp_id": "a", "values": {"description": "Vendor LED", "unit_cost": 280000}},
				{"op": "add", "parent_key": led, "values": {"description": "Transport", "qty": 2, "unit_cost": 15000}},
				{"op": "add", "parent_key": led, "values": {"description": "Contingency", "row_type": "Adjustment", "adj_percent": 10}},
			]
		)
		self.assertIn("a", result["created"])
		baseline = self.reload()
		category = next(row for row in baseline.items if row.row_key == led)
		self.assertEqual(flt(category.cost_amount), 341000)  # (280000 + 30000) * 1.10
		self.assertEqual(flt(baseline.total_cost), 341000)
		self.assertEqual(flt(baseline.total_profit), 1450000 - 341000)
		self.assertAlmostEqual(baseline.margin_pct, (1450000 - 341000) / 1450000 * 100, places=4)

	def test_split_keeps_row_key_and_moves_cost_into_first_line(self):
		led = self.categories()[0].row_key
		self.ops([{"op": "add", "parent_key": led, "temp_id": "v", "values": {"description": "Vendor", "unit_cost": 100}}])
		vendor = next(row for row in self.reload().items if row.description == "Vendor")
		self.ops([{"op": "split", "row_key": vendor.row_key}])
		items = {row.row_key: row for row in self.reload().items}
		split = items[vendor.row_key]
		self.assertEqual((split.row_type, flt(split.cost_amount)), ("Category", 100))
		first = next(row for row in items.values() if row.parent_key == vendor.row_key)
		self.assertEqual((first.description, flt(first.cost_amount)), ("Vendor", 100))
		self.ops([{"op": "add", "parent_key": vendor.row_key, "values": {"description": "Panels", "unit_cost": 70}}])
		self.assertEqual(flt(self.reload().total_cost), 170)

	def test_category_first_line_copies_name_and_follows_rename(self):
		category = self.categories()[0]
		first = next(row for row in self.reload().items if row.parent_key == category.row_key)
		self.assertEqual((first.description, first.row_type), (category.description, "Cost Item"))
		self.ops([{"op": "update", "row_key": first.row_key, "values": {"unit_cost": 280000}}])
		self.assertEqual(flt(self.reload().total_cost), 280000)  # category priced by its first line
		self.ops([{"op": "update", "row_key": category.row_key, "values": {"description": "LED Wall"}}])
		first = next(row for row in self.reload().items if row.row_key == first.row_key)
		self.assertEqual(first.description, "LED Wall")
		self.ops([{"op": "update", "row_key": first.row_key, "values": {"description": "Vendor panels"}}])
		self.ops([{"op": "update", "row_key": category.row_key, "values": {"description": "LED Screens"}}])
		first = next(row for row in self.reload().items if row.row_key == first.row_key)
		self.assertEqual(first.description, "Vendor panels")  # a renamed first line is left alone

	def test_initial_values_come_from_quotation_item(self):
		quotation = make_quotation(((3, 1000),))
		revision = frappe.get_doc(REVISION, f"{planning_api.open_for('Quotation', quotation.name)}-V01")
		category = next(row for row in revision.items if row.row_type == "Category")
		line = next(row for row in revision.items if row.row_type == "Cost Item")
		item = quotation.items[0]
		self.assertEqual((category.qty, category.uom), (item.qty, item.uom))
		self.assertEqual((line.qty, line.uom, flt(line.unit_cost)), (item.qty, item.uom, 1000))
		self.assertEqual(flt(category.cost_amount), 3000)
		self.assertEqual(flt(category.unit_cost), 1000)  # derived: total cost / qty
		self.assertEqual(flt(category.selling_amount), 3000)

	def test_category_qty_uom_unit_cost_are_read_only(self):
		category = self.categories()[0]
		for field, value in (("qty", 5), ("uom", "Box"), ("unit_cost", 10)):
			with self.assertRaises(frappe.ValidationError):
				self.ops([{"op": "update", "row_key": category.row_key, "values": {field: value}}])
		result = self.ops([{"op": "add", "temp_id": "c", "values": {"row_type": "Category", "description": "X", "qty": 9, "unit_cost": 9}}])
		added = next(row for row in self.reload().items if row.row_key == result["created"]["c"])
		self.assertEqual(flt(added.unit_cost), 0)

	def test_category_unit_cost_and_user_category_follow_lines(self):
		quotation = make_quotation(((3, 1000),))
		revision = frappe.get_doc(REVISION, f"{planning_api.open_for('Quotation', quotation.name)}-V01")
		category = next(row for row in revision.items if row.row_type == "Category")
		self.baseline = revision
		self.ops([{"op": "add", "parent_key": category.row_key, "values": {"description": "Extra", "unit_cost": 2000}}])
		category = next(row for row in self.reload().items if row.row_key == category.row_key)
		self.assertEqual(flt(category.cost_amount), 5000)
		self.assertAlmostEqual(category.unit_cost, 5000 / 3)
		result = self.ops([{"op": "add", "temp_id": "c", "values": {"row_type": "Category", "description": "Mine"}}])
		mine = result["created"]["c"]
		first = next(row for row in self.reload().items if row.parent_key == mine)
		self.ops([{"op": "update", "row_key": first.row_key, "values": {"qty": 4, "unit_cost": 50}}])
		mine_row = next(row for row in self.reload().items if row.row_key == mine)
		self.assertEqual((flt(mine_row.qty), flt(mine_row.unit_cost), flt(mine_row.cost_amount)), (4, 50, 200))

	def test_quotation_changes_are_reported_then_refreshed_on_request(self):
		quotation = make_quotation(((1, 1000),))
		plan = planning_api.open_for("Quotation", quotation.name)
		self.baseline = frappe.get_doc(REVISION, f"{plan}-V01")
		category = next(row for row in self.baseline.items if row.row_type == "Category")
		quotation = frappe.get_doc("Quotation", quotation.name)
		quotation.items[0].qty = 2
		quotation.items[0].rate = 1200
		quotation.save()
		status = planning_api.sync_summary("Quotation", quotation.name)
		change = status["changes"][0]
		self.assertEqual((change["qty"], change["selling"]), ([1, 2], [1000, 2400]))
		self.ops([{"op": "add", "parent_key": category.row_key, "values": {"description": "unrelated edit"}}])
		self.assertEqual(flt(self.reload().total_selling), 1000)  # saving never refreshes selling silently
		self.ops([{"op": "refresh_source"}])
		baseline = self.reload()
		category = next(row for row in baseline.items if row.row_key == category.row_key)
		line = next(row for row in baseline.items if row.parent_key == category.row_key)
		self.assertEqual((flt(category.qty), flt(category.selling_amount), flt(baseline.total_selling)), (2, 2400, 2400))
		self.assertEqual((flt(line.qty), flt(line.unit_cost)), (2, 1200))  # untouched line follows qty and rate
		self.assertTrue(planning_api.sync_summary("Quotation", quotation.name)["in_sync"])

	def test_refresh_keeps_values_the_planner_edited(self):
		quotation = make_quotation(((1, 1000),))
		plan = planning_api.open_for("Quotation", quotation.name)
		self.baseline = frappe.get_doc(REVISION, f"{plan}-V01")
		line = next(row for row in self.baseline.items if row.row_type == "Cost Item")
		self.ops([{"op": "update", "row_key": line.row_key, "values": {"unit_cost": 700, "qty": 5}}])
		quotation = frappe.get_doc("Quotation", quotation.name)
		quotation.items[0].qty = 2
		quotation.items[0].rate = 1200
		quotation.save()
		self.ops([{"op": "refresh_source"}])
		line = next(row for row in self.reload().items if row.row_key == line.row_key)
		self.assertEqual((flt(line.qty), flt(line.unit_cost)), (5, 700))

	def test_new_category_gets_first_line(self):
		result = self.ops([{"op": "add", "temp_id": "c", "values": {"row_type": "Category", "description": "Transport"}}])
		key = result["created"]["c"]
		kids = [row for row in self.reload().items if row.parent_key == key]
		self.assertEqual([(k.description, k.row_type) for k in kids], [("Transport", "Cost Item")])

	def test_sync_detects_new_and_removed_items_and_adds_them(self):
		self.assertTrue(planning_api.sync_summary("Quotation", self.quotation.name)["in_sync"])
		quotation = frappe.get_doc("Quotation", self.quotation.name)
		extra_item = frappe.get_all("Item", filters={"disabled": 0}, pluck="name", limit=5)[-1]
		quotation.append("items", {"item_code": extra_item, "item_name": "Rigging", "qty": 2, "rate": 5000})
		quotation.save()
		status = planning_api.sync_summary("Quotation", self.quotation.name)
		self.assertFalse(status["in_sync"])
		self.assertEqual([item["label"] for item in status["new_items"]], ["Rigging"])
		self.ops([{"op": "sync_source"}])
		baseline = self.reload()
		rigging = next(row for row in baseline.items if row.description == "Rigging")
		self.assertEqual((rigging.row_type, rigging.parent_key or "", flt(rigging.selling_amount)), ("Category", "", 10000))
		self.assertTrue([row for row in baseline.items if row.parent_key == rigging.row_key])
		self.assertEqual(flt(baseline.total_selling), 1460000)
		self.assertTrue(planning_api.sync_summary("Quotation", self.quotation.name)["in_sync"])
		quotation = frappe.get_doc("Quotation", self.quotation.name)
		quotation.items = [item for item in quotation.items if item.item_name != "Rigging"]
		quotation.save()
		status = planning_api.sync_summary("Quotation", self.quotation.name)
		self.assertEqual([item["label"] for item in status["removed_items"]], ["Rigging"])
		self.ops([{"op": "update", "row_key": rigging.row_key, "values": {"notes": "still editable"}}])  # dangling link must not block edits

	def test_tree_guards(self):
		led, lighting = (row.row_key for row in self.categories()[:2])
		self.ops([{"op": "add", "parent_key": led, "values": {"description": "Leaf", "unit_cost": 1}}])
		leaf = next(row for row in self.reload().items if row.description == "Leaf")
		with self.assertRaises(frappe.ValidationError):
			self.ops([{"op": "add", "parent_key": leaf.row_key, "values": {"description": "Nope"}}])
		with self.assertRaises(frappe.ValidationError):
			self.ops([{"op": "move", "row_key": led, "parent_key": led}])
		self.ops([{"op": "move", "row_key": leaf.row_key, "parent_key": lighting}])
		self.assertEqual(next(r for r in self.reload().items if r.row_key == leaf.row_key).parent_key, lighting)

	def test_indent_outdent_duplicate_delete(self):
		led, lighting, _technical = (row.row_key for row in self.categories())
		self.ops([{"op": "indent", "row_key": lighting}])
		self.assertEqual(next(r for r in self.reload().items if r.row_key == lighting).parent_key, led)
		self.ops([{"op": "outdent", "row_key": lighting}])
		self.assertEqual(next(r for r in self.reload().items if r.row_key == lighting).parent_key, "")
		self.ops([{"op": "add", "parent_key": led, "values": {"description": "Cable", "unit_cost": 10}}])
		self.ops([{"op": "duplicate", "row_key": led}])
		self.assertEqual(sum(1 for r in self.reload().items if r.description == "Cable"), 2)
		self.assertEqual(flt(self.baseline.total_cost), 20)
		self.ops([{"op": "delete", "row_key": led}])
		self.assertEqual(flt(self.reload().total_cost), 10)
		self.assertFalse([link for link in self.baseline.item_links if link.row_key == led])

	def test_depth_limit(self):
		parent = self.categories()[0].row_key
		with self.assertRaises(frappe.ValidationError):
			for index in range(tree.MAX_DEPTH + 1):
				result = self.ops([{"op": "add", "parent_key": parent, "temp_id": "n", "values": {"row_type": "Category", "description": f"L{index}"}}])
				parent = result["created"]["n"]

	def test_links_must_belong_to_source_document(self):
		other = make_quotation(((1, 5),))
		foreign = other.items[0].name
		with self.assertRaises(frappe.ValidationError):
			self.ops(
				[
					{
						"op": "set_links",
						"row_key": self.categories()[0].row_key,
						"links": [{"link_doctype": "Quotation Item", "link_name": foreign}],
					}
				]
			)

	def test_allocation_split_across_rows(self):
		first, second = (row.row_key for row in self.categories()[:2])
		item = self.quotation.items[0].name
		link = lambda pct: [{"link_doctype": "Quotation Item", "link_name": item, "allocation_pct": pct}]
		self.ops([{"op": "set_links", "row_key": first, "links": link(60)}, {"op": "set_links", "row_key": second, "links": link(40)}])
		rows = {row.row_key: row for row in self.reload().items}
		self.assertEqual(flt(rows[first].selling_amount), 510000)
		self.assertEqual(flt(rows[second].selling_amount), 340000)

	def test_frozen_version_is_immutable_and_reopen_needs_reason(self):
		version_api.freeze(self.baseline.name)
		with self.assertRaises(frappe.PermissionError):
			self.ops([{"op": "add", "values": {"description": "late"}}])
		direct = self.reload()
		direct.append("items", {"row_key": "zzzzzzzz", "row_type": "Cost Item", "description": "sneaky"})
		with self.assertRaises(frappe.ValidationError):
			direct.save()
		with self.assertRaises(frappe.ValidationError):
			version_api.reopen(self.baseline.name, "  ")
		version_api.reopen(self.baseline.name, "Correct vendor price")
		self.ops([{"op": "add", "values": {"description": "fixed", "unit_cost": 5}}])
		self.assertEqual(flt(self.reload().total_cost), 5)

	def test_workspace_payload(self):
		led = self.categories()[0].row_key
		self.ops([{"op": "add", "parent_key": led, "values": {"description": "Transport", "unit_cost": 30000}}])
		frappe.get_doc(
			{"doctype": "Commercial Planning Actual", "planning": self.plan, "row_key": led, "amount": 25000, "posting_date": nowdate()}
		).insert()
		payload = planning_api.get_workspace(self.plan)
		self.assertEqual([c["key"] for c in payload["columns"]], ["v1"])
		self.assertEqual(payload["summary"]["selling"], 1450000)
		self.assertEqual(payload["summary"]["costs"]["quotation"], 30000)
		self.assertEqual([r["depth"] for r in payload["rows"]], [0, 1, 1, 0, 1, 0, 1])
		self.assertTrue(payload["sync"][self.baseline.name]["in_sync"])
		self.assertEqual(payload["actuals"]["rows"][led]["Actual"], 25000)

	def test_user_without_planning_role_is_denied(self):
		user = "no.plan.role@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Plain", "send_welcome_email": 0, "roles": [{"role": "Sales User"}]}).insert()
		frappe.set_user(user)
		with self.assertRaises(frappe.PermissionError):
			planning_api.open_for("Quotation", self.quotation.name)
		frappe.set_user("Administrator")
