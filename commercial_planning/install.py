import frappe

ROLES = ("Commercial Planner", "Commercial Management")

COST_TYPES = (
	"Vendor",
	"Internal Service",
	"Equipment",
	"Material",
	"Labor",
	"Transport",
	"Subcontract",
	"Stock",
	"Miscellaneous",
	"Contingency",
)

COST_SOURCES = (
	"Manual",
	"ERPNext Item",
	"Vendor Quote",
	"Internal Rate",
	"Stock Valuation",
	"Subcontract",
)

STAGES = ("Quotation", "Sales Order", "Project", "Execution")
PURPOSES = ("Estimate", "Pricing", "Budget", "Forecast", "Revision", "Final")

PLANNER, MANAGEMENT, PROJECTS = "Commercial Planner", "Commercial Management", "Projects Manager"

TEMPLATES = (
	{
		"template_name": "Quotation",
		"version_name": "Quotation",
		"stage": "Quotation",
		"purpose": "Estimate",
		"trigger": "Plan created",
		"copy_from": "Blank",
		"reference_role": "Baseline",
		"freeze_source": 0,
		"requires_approval": 0,
		"roles": (PLANNER,),
	},
	{
		"template_name": "Sales Order",
		"version_name": "Sales Order",
		"stage": "Sales Order",
		"purpose": "Pricing",
		"trigger": "Sales Order created",
		"copy_from": "Latest version",
		"reference_role": "",
		"freeze_source": 1,
		"requires_approval": 0,
		"roles": (PLANNER,),
	},
	{
		"template_name": "Project Budget",
		"version_name": "Project Budget",
		"stage": "Project",
		"purpose": "Budget",
		"trigger": "Project created",
		"copy_from": "Latest version",
		"reference_role": "Budget",
		"freeze_source": 1,
		"requires_approval": 1,
		"roles": (PLANNER, PROJECTS),
	},
	{
		"template_name": "Forecast",
		"version_name": "Forecast",
		"stage": "Execution",
		"purpose": "Forecast",
		"trigger": "Manual",
		"copy_from": "Latest version",
		"reference_role": "Forecast",
		"freeze_source": 0,
		"requires_approval": 0,
		"roles": (PLANNER, PROJECTS),
	},
)


def before_install():
	ensure_roles()


def before_migrate():
	ensure_roles()


def after_install():
	ensure_seed_data()


def after_migrate():
	ensure_seed_data()


def ensure_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def ensure_seed_data():
	seed("Commercial Cost Type", "cost_type_name", COST_TYPES)
	seed("Commercial Cost Source", "cost_source_name", COST_SOURCES)
	seed("Commercial Version Stage", "stage_name", STAGES)
	seed("Commercial Version Purpose", "purpose_name", PURPOSES)
	for template in TEMPLATES:
		if frappe.db.exists("Commercial Version Template", template["template_name"]):
			continue
		data = {key: value for key, value in template.items() if key != "roles"}
		doc = frappe.get_doc({"doctype": "Commercial Version Template", **data})
		for role in template["roles"]:
			doc.append("editor_roles", {"role": role})
		doc.insert(ignore_permissions=True)


def seed(doctype, fieldname, values):
	for value in values:
		if not frappe.db.exists(doctype, value):
			frappe.get_doc({"doctype": doctype, fieldname: value}).insert(ignore_permissions=True)
