import frappe
from frappe.tests import IntegrationTestCase

from commercial_planning.api import activity, details
from commercial_planning.api import planning as planning_api
from commercial_planning.api import version as version_api
from commercial_planning.tests.test_planning import make_quotation

VERSION = "Commercial Planning Version"


class TestDetails(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.quotation = make_quotation(((1, 1000), (2, 500)))
		self.plan = planning_api.open_for("Quotation", self.quotation.name)
		self.v1 = frappe.get_doc(VERSION, f"{self.plan}-V01")

	def kinds(self, **kwargs):
		return [event["type"] for event in activity.get_activity(self.plan, **kwargs)]

	def test_activity_lists_creations_changes_comments_and_opens(self):
		line = next(row for row in self.v1.items if row.row_type == "Cost Item")
		planning_api.apply_ops(self.v1.name, [{"op": "update", "row_key": line.row_key, "values": {"unit_cost": 123}}])
		version_api.create(self.plan, reason="Vendor changed price", from_version=self.v1.name, version_name="Vendor Revision", stage="Quotation", purpose="Revision")
		activity.add_comment(self.plan, "Please check the <b>vendor</b> quote")
		activity.log_view(self.plan)
		events = activity.get_activity(self.plan)
		kinds = {event["type"] for event in events}
		self.assertTrue({"created", "change", "comment", "view"} <= kinds)
		created = [event for event in events if event["type"] == "created"]
		self.assertTrue(any("V2 Vendor Revision" in event["summary"] and "from V1" in event["summary"] for event in created))
		self.assertTrue(any(event["detail"] == "Vendor changed price" for event in created))
		change = next(event for event in events if event["type"] == "change")
		self.assertTrue(any("unit cost" in text and "123" in text for text in change["changes"]))
		comment = next(event for event in events if event["type"] == "comment")
		self.assertNotIn("<b>", comment["summary"])  # comments are escaped

	def test_activity_can_be_filtered_to_one_version(self):
		line = next(row for row in self.v1.items if row.row_type == "Cost Item")
		v2 = frappe.get_doc(VERSION, version_api.create(self.plan, reason="split", from_version=self.v1.name, version_name="Two", stage="Quotation", purpose="Revision")["version"])
		planning_api.apply_ops(v2.name, [{"op": "update", "row_key": line.row_key, "values": {"unit_cost": 777}}])
		only_v2 = activity.get_activity(self.plan, version=v2.name)
		self.assertTrue(all(event.get("version", "").startswith("V2") for event in only_v2))
		self.assertTrue(any(event["type"] == "change" for event in only_v2))
		activity.add_comment(self.plan, "plan-level note")
		self.assertNotIn("comment", [event["type"] for event in activity.get_activity(self.plan, version=v2.name)])

	def test_comments_add_list_and_delete(self):
		self.assertEqual(activity.get_comments(self.plan), [])
		comments = activity.add_comment(self.plan, "First\nsecond line")
		self.assertEqual(len(comments), 1)
		self.assertTrue(comments[0]["mine"])
		self.assertIn("<br>", comments[0]["content"])
		with self.assertRaises(frappe.ValidationError):
			activity.add_comment(self.plan, "   ")
		self.assertEqual(activity.delete_comment(self.plan, comments[0]["name"]), [])

	def test_details_assign_tag_and_share(self):
		data = details.get_details(self.plan)
		self.assertEqual((data["assignees"], data["tags"], data["attachments"]), ([], [], []))
		self.assertEqual([doc["doctype"] for doc in data["linked"]], ["Quotation"])
		data = details.assign(self.plan, "Administrator")
		self.assertEqual([a["allocated_to"] for a in data["assignees"]], ["Administrator"])
		data = details.unassign(self.plan, "Administrator")
		self.assertEqual(data["assignees"], [])
		data = details.add_tag(self.plan, "priority")
		self.assertEqual(data["tags"], ["priority"])
		self.assertEqual(details.remove_tag(self.plan, "priority")["tags"], [])
		user = "details.share@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Share", "send_welcome_email": 0, "roles": [{"role": "Commercial Planner"}]}).insert()
		data = details.share_with(self.plan, user, write=1)
		self.assertEqual([(s["user"], s["write"]) for s in data["shared"]], [(user, 1)])
		self.assertEqual(details.unshare(self.plan, user)["shared"], [])

	def test_attachment_removal_is_limited_to_this_plan(self):
		file = frappe.get_doc({"doctype": "File", "file_name": "note.txt", "content": "hello", "attached_to_doctype": "Commercial Planning", "attached_to_name": self.plan, "is_private": 1}).insert()
		data = details.get_details(self.plan)
		self.assertEqual([f["file_name"] for f in data["attachments"]], ["note.txt"])
		other = frappe.get_doc({"doctype": "File", "file_name": "other.txt", "content": "x", "is_private": 1}).insert()
		with self.assertRaises(frappe.ValidationError):
			details.remove_attachment(self.plan, other.name)
		self.assertEqual(details.remove_attachment(self.plan, file.name)["attachments"], [])

	def test_users_without_access_cannot_read_a_plan(self):
		user = "no.access.plan@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Plain", "send_welcome_email": 0, "roles": [{"role": "Sales User"}]}).insert()
		frappe.set_user(user)
		try:
			with self.assertRaises(frappe.PermissionError):
				activity.get_activity(self.plan)
			with self.assertRaises(frappe.PermissionError):
				details.get_details(self.plan)
			with self.assertRaises(frappe.PermissionError):
				activity.add_comment(self.plan, "hi")
		finally:
			frappe.set_user("Administrator")
