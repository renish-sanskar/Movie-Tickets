frappe.ui.form.on("Show", {
	screen(frm) {
		set_ticket_price_from_screen(frm);
	},
});

function set_ticket_price_from_screen(frm) {
	if (!frm.doc.screen || frm.doc.ticket_price) {
		return;
	}

	frappe.db.get_value("Screen", frm.doc.screen, "base_price").then((response) => {
		const base_price = response.message?.base_price;

		if (base_price) {
			frm.set_value("ticket_price", base_price);
		}
	});
}
