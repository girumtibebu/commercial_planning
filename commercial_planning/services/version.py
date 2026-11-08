"""Plan lifecycle: plans, versions, templates, document conversions, freezing/approving, reference roles."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from commercial_planning.services import permissions, tree

VERSION = "Commercial Planning Version"
PLAN = "Commercial Planning"
TEMPLATE = "Commercial Version Template"
ROLES = ("Baseline", "Budget", "Forecast")
ROLE_FIELD = {"Baseline": "baseline_version", "Budget": "budget_version", "Forecast": "forecast_version"}
FROZEN_STATUSES = ("Frozen", "Approved")
PLAN_FIELD = {"Quotation": "quotation", "Sales Order": "sales_order", "Project": "project"}
ITEM_DOCTYPE = {"Quotation": "Quotation Item", "Sales Order": "Sales Order Item"}


def get_plan_for(doctype, name):
	return frappe.db.get_value(PLAN, {PLAN_FIELD[doctype]: name}, "name")


def get_template(trigger):
	name = frappe.db.get_value(TEMPLATE, {"trigger": trigger}, "name", order_by="creation asc")
	return frappe.get_doc(TEMPLATE, name) if name else None


def refresh_stage(plan_name):
	if frappe.db.exists(PLAN, plan_name):
		plan = frappe.get_doc(PLAN, plan_name)
		frappe.db.set_value(PLAN, plan_name, "current_stage", derive_stage(plan), update_modified=False)


# ------------------------------------------------------------------- plans
def create_plan_from_quotation(quotation_name):
	quotation = frappe.get_doc("Quotation", quotation_name)
	if quotation.docstatus == 2:
		frappe.throw(_("Quotation {0} is cancelled").format(quotation.name))
	if quotation.amended_from and get_plan_for("Quotation", quotation.amended_from):
		return follow_amendment(quotation.name)
	plan = frappe.get_doc(
		{
			"doctype": PLAN,
			"title": f"{quotation.customer_name or quotation.party_name} - {quotation.name}",
			"customer": quotation.party_name if quotation.quotation_to == "Customer" else None,
			"opportunity": quotation.get("opportunity"),
			"company": quotation.company,
			"currency": quotation.currency,
			"quotation": quotation.name,
			"created_from": "Quotation",
			"current_stage": "Quotation",
		}
	).insert()
	template = get_template("Plan created")
	first = new_first_version(plan.name, template, "Quotation", "Quotation", "Estimate", "Baseline")
	first.source_doctype, first.source_name = "Quotation", quotation.name
	import_source_items(first, "Quotation Item", quotation.items)
	first.insert()
	return plan.name


def create_plan_from_sales_order(so_name):
	"""A Sales Order with no quotation behind it starts its own plan."""
	order = frappe.get_doc("Sales Order", so_name)
	plan = frappe.get_doc(
		{
			"doctype": PLAN,
			"title": f"{order.customer_name or order.customer} - {order.name}",
			"customer": order.customer,
			"company": order.company,
			"currency": order.currency,
			"sales_order": order.name,
			"created_from": "Sales Order",
			"current_stage": "Sales Order",
		}
	).insert(ignore_permissions=True)
	template = get_template("Sales Order created")
	first = new_first_version(plan.name, template, "Sales Order", "Sales Order", "Pricing", "Baseline")
	first.source_doctype, first.source_name = "Sales Order", order.name
	import_source_items(first, "Sales Order Item", order.items)
	first.insert(ignore_permissions=True)
	return plan.name


def create_plan_from_project(project_name):
	"""A Project with no Sales Order behind it: an empty plan to build the budget in (no selling price)."""
	project = frappe.get_doc("Project", project_name)
	plan = frappe.get_doc(
		{
			"doctype": PLAN,
			"title": f"{project.project_name or project.name} - {project.name}",
			"customer": project.get("customer"),
			"company": project.company,
			"currency": frappe.get_cached_value("Company", project.company, "default_currency"),
			"project": project.name,
			"created_from": "Project",
			"current_stage": "Project",
		}
	).insert(ignore_permissions=True)
	template = get_template("Project created")
	first = new_first_version(plan.name, template, "Project Budget", "Project", "Budget", None)
	first.insert(ignore_permissions=True)
	return plan.name


def new_first_version(plan_name, template, default_name, default_stage, default_purpose, role):
	return frappe.get_doc(
		{
			"doctype": VERSION,
			"planning": plan_name,
			"version_name": (template.version_name or template.template_name) if template else default_name,
			"stage": template.stage if template else default_stage,
			"purpose": template.purpose if template else default_purpose,
			"template": template.name if template else None,
			"reference_role": role,
		}
	)


def import_source_items(version, link_doctype, items):
	for item in items:
		if not item.get("is_alternative"):
			add_source_item(version, link_doctype, item)


def source_rate(item):
	return item.get("net_rate") or item.get("rate") or 0


def add_source_item(version, link_doctype, item):
	"""A document item becomes a top-level Category (linked to it) with a first line of the same name.

	The category takes the item's qty/uom (read-only afterwards); the first line starts with the same
	qty/uom and the item's rate as its unit cost, to be adjusted by the planner.
	"""
	category = version.append(
		"items",
		{
			"row_type": "Category",
			"row_key": frappe.generate_hash(length=8),
			"description": item.item_name or item.item_code,
			"item_code": item.item_code,
			"qty": item.qty,
			"uom": item.uom,
			"source_rate": source_rate(item),
		},
	)
	version.append(
		"item_links",
		{"row_key": category.row_key, "link_doctype": link_doctype, "link_name": item.name, "allocation_pct": 100},
	)
	line = version.append(
		"items",
		{"parent_key": category.row_key, **tree.default_line_values(category), "unit_cost": source_rate(item)},
	)
	return category, line


def next_version_no(planning):
	last = frappe.db.sql("select max(version_no) from `tabCommercial Planning Version` where planning=%s", planning)
	return (last[0][0] or 0) + 1


# ----------------------------------------------------------- reference roles
def get_pointers(planning):
	"""The version holding each reference role (at most one per role)."""
	pointers = {field: None for field in ROLE_FIELD.values()}
	for row in frappe.get_all(VERSION, {"planning": planning, "reference_role": ["in", list(ROLES)]}, ["name", "reference_role"]):
		pointers[ROLE_FIELD[row.reference_role]] = row.name
	return pointers


def refresh_pointers(planning):
	if not frappe.db.exists(PLAN, planning):
		return
	frappe.db.set_value(PLAN, planning, get_pointers(planning), update_modified=False)
	refresh_stage(planning)


def set_reference_role(version, role, system=False):
	"""Give `role` to this version; the version that held it loses it. Empty role clears the flag."""
	if role and role not in ROLES:
		frappe.throw(_("Unknown reference role {0}").format(role))
	if not system:
		if role:
			permissions.require(permissions.can_set_role(version, role), _("You cannot set {0} on {1}").format(role, version.name))
		else:
			permissions.require(permissions.has_any_role(permissions.PLAN_ROLES), _("You cannot change reference roles"))
	if role:
		for holder in frappe.get_all(VERSION, {"planning": version.planning, "reference_role": role, "name": ["!=", version.name]}, pluck="name"):
			frappe.db.set_value(VERSION, holder, "reference_role", None, update_modified=False)
	frappe.db.set_value(VERSION, version.name, "reference_role", role or None, update_modified=False)
	refresh_pointers(version.planning)
	return frappe.get_doc(VERSION, version.name)


# ------------------------------------------------------------- new versions
def copy_version(source, *, version_name, stage, purpose, reason, template=None, source_doctype=None, source_name=None, insert=True, system=False):
	"""New Working version with the same cost tree (same row_keys) as `source`."""
	new = frappe.get_doc(
		{
			"doctype": VERSION,
			"planning": source.planning,
			"version_name": version_name,
			"stage": stage,
			"purpose": purpose,
			"template": template,
			"created_from_version": source.name,
			"source_doctype": source_doctype or source.source_doctype,
			"source_name": source_name or source.source_name,
			"reason": reason,
		}
	)
	for row in source.items:
		new.append("items", row.as_dict(no_default_fields=True))
	for link in source.item_links:
		new.append("item_links", link.as_dict(no_default_fields=True))
	if insert:
		new.insert(ignore_permissions=system)
	return new


def convert_version(source, *, version_name, stage, purpose, reason, source_doctype, source_name, link_map=None, template=None, system=True):
	"""Copy `source` onto a (possibly different) document: re-link its items, add new document items,
	and pull qty / uom / selling from the document. Planner edits to lines are kept."""
	from commercial_planning.services import sync

	new = copy_version(
		source,
		version_name=version_name,
		stage=stage,
		purpose=purpose,
		reason=reason,
		template=template,
		source_doctype=source_doctype,
		source_name=source_name,
		insert=False,
	)
	if link_map is not None:
		rebase_links(new, ITEM_DOCTYPE[source_doctype], link_map)
	view = tree.Tree(new)
	sync.add_missing_items(new, view)
	sync.refresh_rows(new, view)
	view.flush()
	new.insert(ignore_permissions=system)
	return new


def rebase_links(version, item_doctype, link_map):
	"""Point the links at the items of another document; items with no counterpart are dropped."""
	kept = []
	for link in version.item_links:
		target = link_map.get(link.link_name)
		if target:
			link.link_doctype, link.link_name = item_doctype, target
			kept.append(link)
	version.item_links = kept


def create_version(
	planning,
	*,
	from_version=None,
	template=None,
	version_name=None,
	stage=None,
	purpose=None,
	reason=None,
	apply_source_changes=False,
):
	"""Create a version, optionally from a template (defaults + rules) and a source version to copy."""
	permissions.require(permissions.can_view_plans(), _("You cannot create versions"))
	frappe.has_permission(PLAN, "write", doc=planning, throw=True)
	tpl = frappe.get_doc(TEMPLATE, template) if template else None
	source = frappe.get_doc(VERSION, from_version) if from_version else resolve_source(planning, tpl)
	if not source:
		frappe.throw(_("Choose the version to create this one from"))
	if source.planning != planning:
		frappe.throw(_("{0} belongs to another plan").format(source.name))
	fields = {
		"version_name": version_name or (tpl.version_name or tpl.template_name if tpl else None) or source.version_name,
		"stage": stage or (tpl.stage if tpl else source.stage),
		"purpose": purpose or (tpl.purpose if tpl else source.purpose),
		"reason": reason,
		"template": tpl.name if tpl else None,
	}
	if apply_source_changes and source.source_doctype in ITEM_DOCTYPE:
		new = convert_version(
			source, source_doctype=source.source_doctype, source_name=source.source_name, system=False, **fields
		)
	else:
		new = copy_version(source, **fields)
	finish_template(source, new, tpl)
	return new


def finish_template(source, new, tpl):
	if not tpl:
		return
	if tpl.freeze_source and source.status == "Working":
		freeze(source, system=True)
	if tpl.reference_role in ("Baseline", "Forecast"):
		set_reference_role(new, tpl.reference_role, system=True)


def resolve_source(planning, template):
	"""Which version a template copies from when the caller does not choose."""
	if template and template.copy_from == "Blank":
		return None
	if template and template.copy_from == "Baseline version":
		name = frappe.db.get_value(VERSION, {"planning": planning, "reference_role": "Baseline"}, "name")
	else:
		name = frappe.db.get_value(VERSION, {"planning": planning}, "name", order_by="version_no desc")
	return frappe.get_doc(VERSION, name) if name else None


# ------------------------------------------------- document conversions
def plan_for_sales_order(order):
	existing = get_plan_for("Sales Order", order.name)
	if existing:
		return existing
	for quotation in dict.fromkeys(item.prevdoc_docname for item in order.items if item.get("prevdoc_docname")):
		plan = get_plan_for("Quotation", quotation)
		if plan:
			return plan
	return None


def link_sales_order(so_name):
	"""Attach a Sales Order to its quotation's plan (creating the Sales Order version), or start a plan from it."""
	order = frappe.get_doc("Sales Order", so_name)
	plan_name = plan_for_sales_order(order)
	if not plan_name:
		return create_plan_from_sales_order(so_name)
	plan = frappe.get_doc(PLAN, plan_name)
	if plan.sales_order == order.name:
		return plan_name
	if plan.sales_order:
		frappe.msgprint(
			_("Commercial Planning {0} is already linked to {1}; {2} was not added to it.").format(plan.name, plan.sales_order, order.name),
			indicator="orange",
			alert=True,
		)
		return None
	frappe.db.set_value(PLAN, plan_name, "sales_order", order.name, update_modified=False)
	template = get_template("Sales Order created")
	source = resolve_source(plan_name, template)
	if source:
		convert_version(
			source,
			version_name=(template.version_name or template.template_name) if template else "Sales Order",
			stage=template.stage if template else "Sales Order",
			purpose=template.purpose if template else "Pricing",
			reason=_("Created from Sales Order {0}").format(order.name),
			source_doctype="Sales Order",
			source_name=order.name,
			link_map={item.quotation_item: item.name for item in order.items if item.get("quotation_item")},
			template=template.name if template else None,
		)
		if template and template.freeze_source and source.status == "Working":
			freeze(source, system=True)
	refresh_stage(plan_name)
	return plan_name


def link_project(project_name):
	"""Attach a Project to its Sales Order's plan (creating the Project Budget version), or start a plan from it."""
	project = frappe.get_doc("Project", project_name)
	existing = get_plan_for("Project", project.name)
	if existing:
		return existing
	order = project.get("sales_order")
	plan_name = (get_plan_for("Sales Order", order) or link_sales_order(order)) if order else None
	if not plan_name:
		return create_plan_from_project(project.name)
	plan = frappe.get_doc(PLAN, plan_name)
	if plan.project:
		frappe.msgprint(
			_("Commercial Planning {0} is already linked to {1}; {2} was not added to it.").format(plan.name, plan.project, project.name),
			indicator="orange",
			alert=True,
		)
		return None
	frappe.db.set_value(PLAN, plan_name, "project", project.name, update_modified=False)
	template = get_template("Project created")
	source = resolve_source(plan_name, template)
	if source:
		new = copy_version(
			source,
			version_name=(template.version_name or template.template_name) if template else "Project Budget",
			stage=template.stage if template else "Project",
			purpose=template.purpose if template else "Budget",
			reason=_("Created from Project {0}").format(project.name),
			template=template.name if template else None,
			system=True,
		)
		finish_template(source, new, template)
	refresh_stage(plan_name)
	return plan_name


def amendment_map(old_name, new_name):
	"""Match an amended quotation's items to the original's by item code and order of appearance."""
	fields = ["name", "item_code"]
	filters = {"parenttype": "Quotation"}
	pool = {}
	for item in frappe.get_all("Quotation Item", {**filters, "parent": new_name}, fields, order_by="idx asc"):
		pool.setdefault(item.item_code, []).append(item.name)
	mapping = {}
	for item in frappe.get_all("Quotation Item", {**filters, "parent": old_name}, fields, order_by="idx asc"):
		queue = pool.get(item.item_code)
		if queue:
			mapping[item.name] = queue.pop(0)
	return mapping


def follow_amendment(quotation_name):
	"""A quotation amended after a plan exists: the plan follows it with a new version bound to the amendment."""
	quotation = frappe.get_doc("Quotation", quotation_name)
	old_name = quotation.amended_from
	plan_name = get_plan_for("Quotation", old_name) if old_name else None
	if not plan_name:
		return None
	versions = frappe.get_all(VERSION, {"planning": plan_name}, ["name", "source_name"], order_by="version_no desc")
	source_name = next((v.name for v in versions if v.source_name == old_name), versions[0].name)
	source = frappe.get_doc(VERSION, source_name)
	frappe.db.set_value(PLAN, plan_name, "quotation", quotation.name, update_modified=False)
	convert_version(
		source,
		version_name=f"{source.version_name} (amended)",
		stage=source.stage,
		purpose="Revision",
		reason=_("Quotation amended: {0} → {1}").format(old_name, quotation.name),
		source_doctype="Quotation",
		source_name=quotation.name,
		link_map=amendment_map(old_name, quotation.name),
	)
	if source.status == "Working":
		freeze(source, system=True)
	return plan_name


# ---------------------------------------------------------------- statuses
def freeze(version, system=False):
	if not system:
		permissions.require(permissions.can_freeze_version(version), _("You cannot freeze {0}").format(version.name))
	version.status = "Frozen"
	version.frozen_by = frappe.session.user
	version.frozen_on = now_datetime()
	version.flags.ignore_permissions = system
	version.save()
	return version


def approve(version):
	permissions.require(permissions.can_approve_version(version), _("Only Commercial Management can approve {0}").format(version.name))
	version.flags.allow_frozen_write = True
	version.status = "Approved"
	version.approved_by = frappe.session.user
	version.approved_on = now_datetime()
	if not version.frozen_on:
		version.frozen_by, version.frozen_on = version.approved_by, version.approved_on
	version.save()
	role = frappe.db.get_value(TEMPLATE, version.template, "reference_role") if version.template else None
	if role == "Budget":
		return set_reference_role(version, "Budget")
	return version


def reopen(version, reason):
	permissions.require(permissions.can_reopen_version(version), _("Only Commercial Management can reopen a version"))
	if not (reason or "").strip():
		frappe.throw(_("A reason is required to reopen a version"))
	version.flags.allow_frozen_write = True
	version.status = "Working"
	version.frozen_by = version.frozen_on = version.approved_by = version.approved_on = None
	version.save()
	if version.reference_role == "Budget":
		version = set_reference_role(version, None, system=True)
	version.add_comment("Info", _("Reopened by {0}: {1}").format(frappe.session.user, reason))
	return version


def derive_stage(plan):
	if plan.status == "Cancelled":
		return "Cancelled"
	if plan.project:
		if frappe.db.get_value("Project", plan.project, "status") == "Completed":
			return "Completed"
		if frappe.db.exists(VERSION, {"planning": plan.name, "reference_role": "Budget", "status": "Approved"}):
			return "Execution"
		return "Project"
	if plan.sales_order:
		return "Sales Order"
	return "Quotation"
