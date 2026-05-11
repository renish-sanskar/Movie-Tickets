frappe.ui.form.on("Booked Seat", {
	seats_add(frm, cdt, cdn) {
		set_booked_seat_price(frm, cdt, cdn);
	},
});

function set_booked_seat_price(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (row.seat_price) {
		return;
	}

	if (frm.doc.price_per_seat) {
		frappe.model.set_value(cdt, cdn, "seat_price", frm.doc.price_per_seat);
		return;
	}

	if (!frm.doc.show) {
		return;
	}

	frappe.db.get_value("Show", frm.doc.show, "ticket_price").then((response) => {
		const ticket_price = response.message?.ticket_price;

		if (ticket_price) {
			frm.set_value("price_per_seat", ticket_price);
			frappe.model.set_value(cdt, cdn, "seat_price", ticket_price);
		}
	});
}
