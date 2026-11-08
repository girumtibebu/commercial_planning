// Opens the Commercial Planning workspace (a Vue SPA served by this app) as a full-viewport overlay.
window.commercial_planning = window.commercial_planning || {};

(function (cp) {
	const ROLES = ["Commercial Planner", "Commercial Management", "Projects Manager", "System Manager"];

	cp.has_access = () => ROLES.some((role) => frappe.user.has_role(role));

	cp.add_button = function (frm) {
		if (frm.is_new() || !cp.has_access()) return;
		frm.add_custom_button(__("Commercial Planning"), () => cp.open(frm));
	};

	// Tell the user when the document has items the plan does not know about (or lost some).
	cp.show_sync_notice = function (frm) {
		if (frm.is_new() || !cp.has_access()) return;
		frappe
			.call({
				method: "commercial_planning.api.planning.sync_summary",
				args: { doctype: frm.doctype, name: frm.doc.name },
			})
			.then((r) => {
				const status = r.message;
				if (!status || status.in_sync) return;
				const parts = [];
				if (status.new_items?.length) {
					const names = status.new_items.map((i) => frappe.utils.escape_html(i.label)).join(", ");
					parts.push(__("{0} new item(s) not in Commercial Planning: {1}", [status.new_items.length, names]));
				}
				if (status.removed_items?.length) {
					parts.push(__("{0} planned item(s) no longer on this document", [status.removed_items.length]));
				}
				if (status.changes?.length) {
					parts.push(__("qty, unit or selling price changed on {0} planned item(s)", [status.changes.length]));
				}
				frm.dashboard.add_comment(
					`${parts.join(" · ")} — <a href="#" class="cp-open-plan">${__("Open Commercial Planning")}</a>`,
					"orange",
					true
				);
				frm.dashboard.wrapper.find(".cp-open-plan").on("click", (e) => {
					e.preventDefault();
					cp.open(frm);
				});
			});
	};

	// Opens the planning workspace in its own tab (a full Vue app served by this app).
	cp.open = function (frm) {
		const tab = window.open("", "_blank");
		frappe
			.call({
				method: "commercial_planning.api.planning.open_for",
				args: { doctype: frm.doctype, name: frm.doc.name },
				freeze: true,
				freeze_message: __("Opening Commercial Planning..."),
			})
			.then((r) => {
				const query = `?from=${encodeURIComponent(frm.doctype)}&name=${encodeURIComponent(frm.doc.name)}`;
				const url = `/commercial-planning/plan/${encodeURIComponent(r.message)}/plan${query}`;
				if (tab) tab.location.href = url;
				else window.location.href = url;
			})
			.catch(() => tab && tab.close());
	};
})(window.commercial_planning);
