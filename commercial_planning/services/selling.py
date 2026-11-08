"""Selling side of a revision: read from Quotation / Sales Order items, never typed."""

import frappe
from frappe import _
from frappe.utils import flt

SOURCE_ITEM_DOCTYPE = {
	"Quotation": "Quotation Item",
	"Sales Order": "Sales Order Item",
}


def get_item_amounts(link_doctype, names):
	if not names:
		return {}
	rows = frappe.get_all(
		link_doctype, filters={"name": ["in", list(names)]}, fields=["name", "parent", "net_amount"]
	)
	return {row.name: row for row in rows}


def validate_links(revision):
	"""Every link must point to an item of the document this revision is tied to."""
	expected = SOURCE_ITEM_DOCTYPE.get(revision.source_doctype)
	for doctype in {link.link_doctype for link in revision.item_links}:
		if expected and doctype != expected:
			frappe.throw(_("A version built on {0} can only link {1}").format(revision.source_doctype, expected))
		names = [link.link_name for link in revision.item_links if link.link_doctype == doctype]
		found = get_item_amounts(doctype, names)
		for name in names:
			# an item deleted from the document is reported by sync, it must not block editing
			if name in found and found[name].parent != revision.source_name:
				frappe.throw(_("{0} {1} does not belong to {2}").format(doctype, name, revision.source_name))


def refresh_selling(revision, row_keys=None):
	"""Re-read selling_amount from the linked items (all rows, or only `row_keys`) and refresh the total."""
	by_doctype = {}
	for link in revision.item_links:
		by_doctype.setdefault(link.link_doctype, set()).add(link.link_name)
	amounts = {doctype: get_item_amounts(doctype, names) for doctype, names in by_doctype.items()}
	selling = {}
	for link in revision.item_links:
		item = amounts[link.link_doctype].get(link.link_name)
		if item:
			share = flt(link.allocation_pct) / 100
			selling[link.row_key] = selling.get(link.row_key, 0) + flt(item.net_amount) * share
	for row in revision.items:
		if row_keys is None or row.row_key in row_keys:
			row.selling_amount = selling.get(row.row_key, 0)
	refresh_totals(revision)


def refresh_totals(revision):
	revision.total_selling = sum(flt(row.selling_amount) for row in revision.items)
