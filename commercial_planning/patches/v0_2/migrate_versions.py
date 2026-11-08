import frappe

from commercial_planning.install import ensure_seed_data
from commercial_planning.services import version as version_service

VERSION = "Commercial Planning Version"
PLAN = "Commercial Planning"

# old fixed stage -> (stage, purpose, name, reference role)
STAGE_MAP = {
	"Quotation Baseline": ("Quotation", "Estimate", "Quotation", "Baseline"),
	"Sales Order Revision": ("Sales Order", "Pricing", "Sales Order", None),
	"Project Budget": ("Project", "Budget", "Project Budget", "Budget"),
	"Forecast Revision": ("Execution", "Forecast", "Forecast", "Forecast"),
}


def execute():
	ensure_seed_data()
	if not frappe.db.has_column(VERSION, "rev_no"):
		return
	rows = frappe.db.sql(
		f"select name, planning, rev_no, stage, source_revision from `tab{VERSION}`", as_dict=True
	)
	for row in rows:
		stage, purpose, name, role = STAGE_MAP.get(row.stage, ("Quotation", "Estimate", row.stage, None))
		template = frappe.db.get_value("Commercial Version Template", {"stage": stage, "purpose": purpose}, "name")
		frappe.db.set_value(
			VERSION,
			row.name,
			{
				"version_no": row.rev_no,
				"version_name": name,
				"stage": stage,
				"purpose": purpose,
				"reference_role": role,
				"template": template,
				"created_from_version": row.source_revision or None,
			},
			update_modified=False,
		)
	for row in rows:
		frappe.rename_doc(VERSION, row.name, f"{row.planning}-V{row.rev_no:02d}", force=True)
	for plan in frappe.get_all(PLAN, pluck="name"):
		version_service.refresh_pointers(plan)
	drop_columns(VERSION, ("rev_no", "source_revision"))
	drop_columns(PLAN, ("baseline_revision", "budget_revision", "forecast_revision"))


def drop_columns(doctype, columns):
	for column in columns:
		if frappe.db.has_column(doctype, column):
			frappe.db.sql_ddl(f"alter table `tab{doctype}` drop column `{column}`")
