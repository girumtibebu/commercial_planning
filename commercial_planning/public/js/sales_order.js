frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		commercial_planning.add_button(frm);
		commercial_planning.show_sync_notice(frm);
	},
});
