frappe.ui.form.on("Quotation", {
	refresh(frm) {
		commercial_planning.add_button(frm);
		commercial_planning.show_sync_notice(frm);
	},
});
