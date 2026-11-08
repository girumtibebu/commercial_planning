"""Cost tree of a revision: structure rules, row operations and rollups."""

import frappe
from frappe import _
from frappe.utils import flt

MAX_DEPTH = 6
CATEGORY, COST_ITEM, ADJUSTMENT = "Category", "Cost Item", "Adjustment"

EDITABLE_FIELDS = (
	"description",
	"notes",
	"row_type",
	"cost_type",
	"cost_source",
	"item_code",
	"supplier",
	"vendor_quote",
	"qty",
	"uom",
	"unit_cost",
	"cost_currency",
	"exchange_rate",
	"adj_mode",
	"adj_percent",
)


LINE_FIELDS = (
	"description",
	"notes",
	"cost_type",
	"cost_source",
	"item_code",
	"supplier",
	"vendor_quote",
	"qty",
	"uom",
	"unit_cost",
	"cost_currency",
	"exchange_rate",
)


def new_row_key():
	return frappe.generate_hash(length=8)


def default_line_values(category):
	"""First line of a category: same name, quoted qty/uom, no cost yet."""
	return {
		"row_type": COST_ITEM,
		"row_key": new_row_key(),
		"description": category.description,
		"qty": category.qty or 1,
		"uom": category.uom,
	}


class Tree:
	"""Ordered parent/child view over `revision.items`; `flush` writes the order back."""

	def __init__(self, revision):
		self.revision = revision
		self.children = {}
		self.rows = {}
		for row in revision.items:
			self.rows[row.row_key] = row
			self.children.setdefault(row.parent_key or "", []).append(row)

	def get(self, row_key):
		row = self.rows.get(row_key)
		if not row:
			frappe.throw(_("Row {0} does not exist in this revision").format(row_key))
		return row

	def siblings(self, parent_key):
		return self.children.setdefault(parent_key or "", [])

	def depth(self, row_key):
		depth = 0
		while row_key:
			depth += 1
			row_key = self.rows[row_key].parent_key
		return depth

	def subtree(self, row):
		found = [row]
		for child in self.siblings(row.row_key):
			found.extend(self.subtree(child))
		return found

	def height(self, row):
		kids = self.siblings(row.row_key)
		return 1 + max((self.height(kid) for kid in kids), default=0)

	def ordered(self, parent_key=""):
		for row in self.siblings(parent_key):
			yield row
			yield from self.ordered(row.row_key)

	def flush(self):
		ordered = list(self.ordered())
		for index, row in enumerate(ordered, start=1):
			row.idx = index
		self.revision.items = ordered

	def attach(self, row, parent_key, before_key=None):
		self.check_parent(row, parent_key)
		siblings = self.siblings(parent_key)
		row.parent_key = parent_key or ""
		position = len(siblings)
		if before_key:
			position = next((i for i, s in enumerate(siblings) if s.row_key == before_key), position)
		siblings.insert(position, row)
		self.rows[row.row_key] = row

	def detach(self, row):
		self.siblings(row.parent_key).remove(row)

	def check_parent(self, row, parent_key):
		if not parent_key:
			if self.height(row) > MAX_DEPTH:
				frappe.throw(_("Maximum nesting depth is {0}").format(MAX_DEPTH))
			return
		parent = self.get(parent_key)
		if parent.row_type != CATEGORY:
			frappe.throw(_("Rows can only be placed under a Category"))
		if parent in self.subtree(row):
			frappe.throw(_("A row cannot be moved into itself"))
		if self.depth(parent_key) + self.height(row) > MAX_DEPTH:
			frappe.throw(_("Maximum nesting depth is {0}").format(MAX_DEPTH))


def apply_ops(revision, ops):
	"""Apply a list of row operations in order; returns {temp_id: row_key} for added rows."""
	tree = Tree(revision)
	created = {}
	for op in ops:
		handler = OPERATIONS.get(op.get("op"))
		if not handler:
			frappe.throw(_("Unknown operation {0}").format(op.get("op")))
		handler(revision, tree, op, created)
	tree.flush()
	recalculate(revision)
	return created


CATEGORY_CALCULATED = ("qty", "uom", "unit_cost")


def clean_values(values):
	return {key: value for key, value in (values or {}).items() if key in EDITABLE_FIELDS}


def reject_calculated(row, values):
	"""A category's qty, uom and unit cost come from the document item and its lines; they are not typed."""
	if row.row_type == CATEGORY and any(key in values for key in CATEGORY_CALCULATED):
		frappe.throw(_("Quantity, UOM and unit cost of a category are calculated; edit its lines instead"))


def op_add(revision, tree, op, created):
	values = clean_values(op.get("values"))
	if values.get("row_type") == CATEGORY:
		values = {key: value for key, value in values.items() if key not in CATEGORY_CALCULATED}
	row = revision.append("items", {"row_type": COST_ITEM, "qty": 1, **values})
	row.row_key = new_row_key()
	tree.rows[row.row_key] = row
	tree.attach(row, op.get("parent_key"), op.get("before_key"))
	normalise_row(row)
	if row.row_type == CATEGORY:
		add_default_line(revision, tree, row)
	if op.get("temp_id"):
		created[op["temp_id"]] = row.row_key


def add_default_line(revision, tree, category):
	if tree.depth(category.row_key) >= MAX_DEPTH:
		return None
	line = revision.append("items", default_line_values(category))
	tree.rows[line.row_key] = line
	tree.attach(line, category.row_key)
	return line


def op_update(revision, tree, op, created):
	row = tree.get(op["row_key"])
	values = clean_values(op.get("values"))
	new_type = values.get("row_type")
	if new_type and new_type != row.row_type:
		change_type(revision, tree, row, new_type)
	if row.row_type == CATEGORY:
		reject_calculated(row, values)
	previous_name = row.description
	row.update(values)
	normalise_row(row)
	if row.row_type == CATEGORY and "description" in values:
		rename_first_line(tree, row, previous_name)


def rename_first_line(tree, category, previous_name):
	"""A first line still carrying the category's old name follows the rename."""
	lines = tree.siblings(category.row_key)
	first = lines[0] if lines else None
	if first and first.row_type == COST_ITEM and (first.description or "") == (previous_name or ""):
		first.description = category.description


def change_type(revision, tree, row, new_type):
	if row.row_type == CATEGORY and tree.siblings(row.row_key):
		frappe.throw(_("Move or delete the rows under {0} before changing its type").format(row.description))
	if new_type == CATEGORY:
		demote_to_first_line(revision, tree, row)


def demote_to_first_line(revision, tree, row):
	"""Turn a Cost Item into a Category; its own cost moves into a first child line so totals are kept."""
	if tree.depth(row.row_key) >= MAX_DEPTH:
		frappe.throw(_("Maximum nesting depth is {0}").format(MAX_DEPTH))
	line = revision.append("items", {field: row.get(field) for field in LINE_FIELDS})
	line.row_type = COST_ITEM
	line.row_key = new_row_key()
	tree.rows[line.row_key] = line
	for field in ("unit_cost", "supplier", "vendor_quote", "cost_source", "cost_type", "notes"):
		row.set(field, None if field not in ("unit_cost",) else 0)
	row.row_type = CATEGORY
	tree.attach(line, row.row_key)


def op_delete(revision, tree, op, created):
	row = tree.get(op["row_key"])
	doomed = {r.row_key for r in tree.subtree(row)}
	tree.detach(row)
	revision.items = [r for r in revision.items if r.row_key not in doomed]
	revision.item_links = [link for link in revision.item_links if link.row_key not in doomed]
	for key in doomed:
		tree.rows.pop(key, None)
		tree.children.pop(key, None)


def op_move(revision, tree, op, created):
	row = tree.get(op["row_key"])
	tree.check_parent(row, op.get("parent_key"))
	tree.detach(row)
	tree.attach(row, op.get("parent_key"), op.get("before_key"))


def op_indent(revision, tree, op, created):
	row = tree.get(op["row_key"])
	siblings = tree.siblings(row.parent_key)
	index = siblings.index(row)
	if index == 0:
		frappe.throw(_("There is no row above to indent under"))
	new_parent = siblings[index - 1]
	if new_parent.row_type != CATEGORY:
		frappe.throw(_("Rows can only be indented under a Category; split the row above first"))
	tree.detach(row)
	tree.attach(row, new_parent.row_key)


def op_outdent(revision, tree, op, created):
	row = tree.get(op["row_key"])
	if not row.parent_key:
		return
	parent = tree.get(row.parent_key)
	siblings = tree.siblings(parent.parent_key)
	after = siblings[siblings.index(parent) + 1].row_key if siblings.index(parent) + 1 < len(siblings) else None
	tree.detach(row)
	tree.attach(row, parent.parent_key, after)


def op_duplicate(revision, tree, op, created):
	source = tree.get(op["row_key"])
	copies = {}
	for original in tree.subtree(source):
		data = {key: original.get(key) for key in EDITABLE_FIELDS + ("row_type",)}
		copy = revision.append("items", data)
		copy.row_key = new_row_key()
		copies[original.row_key] = copy
		tree.rows[copy.row_key] = copy
	for original_key, copy in copies.items():
		original = tree.rows[original_key]
		if original is source:
			siblings = tree.siblings(source.parent_key)
			after = siblings[siblings.index(source) + 1].row_key if siblings.index(source) + 1 < len(siblings) else None
			tree.attach(copy, source.parent_key, after)
		else:
			tree.attach(copy, copies[original.parent_key].row_key)


def op_split(revision, tree, op, created):
	"""Turn a Cost Item into a Category keeping its row_key so node-level comparison survives."""
	row = tree.get(op["row_key"])
	if row.row_type != COST_ITEM:
		frappe.throw(_("Only a Cost Item can be split"))
	demote_to_first_line(revision, tree, row)
	normalise_row(row)


def op_sync_source(revision, tree, op, created):
	from commercial_planning.services import sync

	sync.add_missing_items(revision, tree, set(op.get("items") or []))


def op_refresh_source(revision, tree, op, created):
	from commercial_planning.services import sync

	sync.refresh_rows(revision, tree, set(op.get("rows") or []))


def op_set_links(revision, tree, op, created):
	row = tree.get(op["row_key"])
	if row.parent_key or row.row_type != CATEGORY:
		frappe.throw(_("Document items can only be linked to top-level Categories"))
	revision.item_links = [link for link in revision.item_links if link.row_key != row.row_key]
	for link in op.get("links") or []:
		revision.append(
			"item_links",
			{
				"row_key": row.row_key,
				"link_doctype": link["link_doctype"],
				"link_name": link["link_name"],
				"allocation_pct": flt(link.get("allocation_pct", 100)),
			},
		)
	from commercial_planning.services import selling

	selling.refresh_selling(revision, {row.row_key})


OPERATIONS = {
	"add": op_add,
	"update": op_update,
	"delete": op_delete,
	"move": op_move,
	"indent": op_indent,
	"outdent": op_outdent,
	"duplicate": op_duplicate,
	"split": op_split,
	"set_links": op_set_links,
	"sync_source": op_sync_source,
	"refresh_source": op_refresh_source,
}


def normalise_row(row):
	if row.row_type != ADJUSTMENT:
		row.adj_mode = None
		row.adj_percent = 0
	elif not row.adj_mode:
		row.adj_mode = "Percent of parent"
	if not row.exchange_rate:
		row.exchange_rate = 1


def recalculate(revision):
	"""Recompute every row's cost_amount bottom-up and the revision totals."""
	view = Tree(revision)
	total = group_cost(view, "")
	derive_category_fields(revision, view)
	revision.total_cost = total
	return total


def derive_category_fields(revision, view):
	"""Category qty/uom follow the document item (or the first line); unit cost = total / qty."""
	linked = {link.row_key for link in revision.item_links}
	for row in revision.items:
		if row.row_type != CATEGORY:
			continue
		first = next(iter(view.siblings(row.row_key)), None)
		if row.row_key not in linked and first and first.row_type == COST_ITEM:
			row.qty, row.uom = first.qty, first.uom
		row.unit_cost = flt(row.cost_amount) / flt(row.qty) if flt(row.qty) else 0


def leaf_cost(row):
	return flt(row.qty) * flt(row.unit_cost) * (flt(row.exchange_rate) or 1)


def group_cost(tree, parent_key):
	"""Cost of one sibling group: leaves + nested categories, then adjustments on that base."""
	base = 0.0
	adjustments = []
	for row in tree.siblings(parent_key):
		if row.row_type == ADJUSTMENT:
			adjustments.append(row)
			continue
		if row.row_type == CATEGORY:
			row.cost_amount = group_cost(tree, row.row_key)
		else:
			row.cost_amount = leaf_cost(row)
		base += flt(row.cost_amount)
	total = base
	for row in adjustments:
		if row.adj_mode == "Fixed":
			row.cost_amount = leaf_cost(row)
		else:
			row.cost_amount = base * flt(row.adj_percent) / 100
		total += flt(row.cost_amount)
	return total
