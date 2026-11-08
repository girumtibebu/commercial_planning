import frappe

OLD = "Commercial Planning Revision"
NEW = "Commercial Planning Version"


def execute():
	"""Revisions became versions; keep the table and its rows."""
	if frappe.db.exists("DocType", OLD) and not frappe.db.exists("DocType", NEW):
		frappe.rename_doc("DocType", OLD, NEW, force=True)
	for doctype in ("Commercial Planning Item", "Commercial Planning Item Link"):
		frappe.db.sql(f"update `tab{doctype}` set parenttype=%s where parenttype=%s", (NEW, OLD))
