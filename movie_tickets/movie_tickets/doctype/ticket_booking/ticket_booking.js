frappe.ui.form.on("Ticket Booking", {
	refresh(frm) {
		show_booking_headline(frm);
		add_select_seats_button(frm);
		add_send_confirmation_button(frm);
		calculate_booking_total(frm);
		show_qr_code(frm);
	},

	async show(frm) {
		frm.clear_table("seats");
		frm.refresh_field("seats");
		await fetch_show_details(frm);
		frm.clear_custom_buttons();
		add_select_seats_button(frm);
		add_send_confirmation_button(frm);
		calculate_booking_total(frm);
	},

	before_cancel(frm) {
		return new Promise((resolve, reject) => {
			frappe.confirm(
				__(
					"Refund policy: cancellations more than 4 hours before the show receive a full refund, 2-4 hours receive 50%, and less than 2 hours receive no refund. Continue?"
				),
				() => resolve(),
				() => {
					frappe.validated = false;
					reject();
				}
			);
		});
	},

	seats_remove(frm) {
		calculate_booking_total(frm);
	},
});

frappe.ui.form.on("Booked Seat", {
	seats_add(frm, cdt, cdn) {
		set_booked_seat_price(frm, cdt, cdn);
		calculate_booking_total(frm);
	},

	seat_price(frm) {
		calculate_booking_total(frm);
	},
});

async function fetch_show_details(frm) {
	if (!frm.doc.show) {
		frm.dashboard.clear_headline();
		return;
	}

	const response = await frappe.db.get_value("Show", frm.doc.show, [
		"movie_title",
		"theater",
		"screen",
		"show_date",
		"start_time",
		"ticket_price",
		"available_seats",
	]);
	const show = response.message;

	if (!show) {
		return;
	}

	await frm.set_value({
		movie_title: show.movie_title,
		theater: show.theater,
		screen: show.screen,
		show_date: show.show_date,
		start_time: show.start_time,
		price_per_seat: show.ticket_price,
	});

	show_booking_headline(frm, show);

	if (show.available_seats < 5) {
		frappe.show_alert({
			message: __("Only {0} seats remaining!", [show.available_seats]),
			indicator: "orange",
		});
	}
}

function show_booking_headline(frm, show) {
	show = show || frm.doc;

	if (!show.show && !show.movie_title) {
		return;
	}

	frm.dashboard.set_headline(
		__("{0} | {1} | {2} | {3} {4} | Price: {5} | Available: {6}", [
			show.movie_title || "-",
			show.theater || "-",
			show.screen || "-",
			show.show_date || "-",
			show.start_time || "-",
			format_currency(show.ticket_price || show.price_per_seat || 0),
			show.available_seats ?? "-",
		])
	);
}

function add_select_seats_button(frm) {
	if (frm.doc.docstatus !== 0 || !frm.doc.show) {
		return;
	}

	frm.add_custom_button(__("Select Seats"), () => {
		if (!frm.doc.screen) {
			frappe.msgprint(__("Please select a Show first to load screen details."));
			return;
		}
		open_seat_selection_dialog(frm);
	});
}

function add_send_confirmation_button(frm) {
	if (frm.doc.docstatus !== 1) {
		return;
	}

	frm.add_custom_button(__("Send Booking Confirmation"), () => {
		frappe.call({
			method:
				"movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.send_booking_confirmation",
			args: { booking: frm.doc.name },
			callback(response) {
				frappe.show_alert({
					message: response.message?.message || __("Booking confirmation sent"),
					indicator: "green",
				});
			},
		});
	});
}

async function open_seat_selection_dialog(frm) {
	const [screen_response, booked_response, max_seats_response] = await Promise.all([
		frappe.call({
			method: "movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.get_screen_layout",
			args: { screen: frm.doc.screen },
		}),
		frappe.call({
			method: "movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.get_booked_seats",
			args: { show: frm.doc.show, booking: frm.doc.name },
		}),
		frappe.call({
			method:
				"movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.get_max_seats_per_booking",
		}),
	]);
	const screen = screen_response.message;
	const booked_seats = new Set(booked_response.message || []);
	const selected_seats = new Set(
		(frm.doc.seats || [])
			.map((seat) => seat.seat_label)
			.filter((seat_label) => !booked_seats.has(seat_label))
	);
	const existing_seat_prices = get_existing_seat_prices(frm);
	const max_seats = cint(max_seats_response.message) || 10;
	const dialog_layout = get_seat_dialog_layout(screen.seat_rows, screen.seats_per_row);

	const dialog = new frappe.ui.Dialog({
		title: __("Select Seats"),
		size: dialog_layout.size,
		fields: [
			{ fieldname: "seat_summary", fieldtype: "HTML" },
			{ fieldname: "seat_grid", fieldtype: "HTML" },
		],
		primary_action_label: __("Confirm"),
		primary_action() {
			if (!selected_seats.size) {
				frappe.msgprint(__("Select at least one seat."));
				return;
			}

			if (selected_seats.size > max_seats) {
				frappe.msgprint(__("You can select a maximum of {0} seats.", [max_seats]));
				return;
			}

			populate_selected_seats(frm, selected_seats, existing_seat_prices);
			dialog.hide();
		},
	});

	refresh_seat_dialog_summary(dialog, selected_seats, max_seats);
	dialog.fields_dict.seat_grid.$wrapper.html(
		build_seat_grid_html(
			screen.seat_rows,
			screen.seats_per_row,
			booked_seats,
			selected_seats,
			dialog_layout
		)
	);

	dialog.fields_dict.seat_grid.$wrapper.on("click", ".seat.available", function () {
		const seat_label = this.dataset.seatLabel;

		if (selected_seats.has(seat_label)) {
			selected_seats.delete(seat_label);
			this.classList.remove("selected");
		} else {
			if (selected_seats.size >= max_seats) {
				frappe.show_alert({
					message: __("You can select a maximum of {0} seats.", [max_seats]),
					indicator: "orange",
				});
				return;
			}

			selected_seats.add(seat_label);
			this.classList.add("selected");
		}

		refresh_seat_dialog_summary(dialog, selected_seats, max_seats);
	});

	dialog.show();
	apply_seat_dialog_size(dialog, dialog_layout);
}

function build_seat_grid_html(rows, columns, booked_seats, selected_seats, dialog_layout) {
	let html = `<style>
		.seat-summary { align-items: center; display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
		.seat-count { font-weight: 600; }
		.seat-legend { align-items: center; display: inline-flex; gap: 5px; }
		.seat-legend-dot { border-radius: 3px; display: inline-block; height: 14px; width: 14px; }
		.seat-grid { display: grid; gap: 8px; max-height: ${dialog_layout.grid_height}; overflow: auto; padding: 8px 0; }
		.seat-row { display: flex; align-items: center; gap: 6px; }
		.seat-row-label { width: 28px; font-weight: 600; }
		.seat { min-width: ${dialog_layout.seat_width}px; height: 32px; border: 0; border-radius: 4px; color: #fff; flex: 0 0 auto; }
		.seat.available { background: #2f9e44; cursor: pointer; }
		.seat.booked { background: #c92a2a; cursor: not-allowed; opacity: 0.8; }
		.seat.selected { background: #1c7ed6; outline: 2px solid #1864ab; }
	</style><div class="seat-grid">`;

	for (let row = 1; row <= rows; row++) {
		const row_letter = row_number_to_letter(row);
		html += `<div class="seat-row"><span class="seat-row-label">${row_letter}</span>`;

		for (let seat_number = 1; seat_number <= columns; seat_number++) {
			const seat_label = `${row_letter}-${seat_number}`;
			const is_booked = booked_seats.has(seat_label);
			const is_selected = !is_booked && selected_seats.has(seat_label);
			const classes = ["seat", is_booked ? "booked" : "available", is_selected ? "selected" : ""]
				.filter(Boolean)
				.join(" ");

			html += `<button type="button" class="${classes}" data-seat-label="${seat_label}" ${
				is_booked ? "disabled" : ""
			}>${seat_number}</button>`;
		}

		html += `</div>`;
	}

	return `${html}</div>`;
}

function get_seat_dialog_layout(rows, columns) {
	rows = cint(rows);
	columns = cint(columns);

	const seat_width = columns > 18 ? 36 : columns > 12 ? 40 : 46;
	const grid_width = 28 + columns * (seat_width + 7) + 72;
	const width = Math.min(Math.max(grid_width, 620), Math.floor(window.innerWidth * 0.96));
	const grid_height = Math.min(Math.max(rows * 40 + 24, 260), Math.floor(window.innerHeight * 0.65));

	return {
		grid_height: `${grid_height}px`,
		seat_width,
		size: columns > 14 ? "extra-large" : columns > 8 ? "large" : "medium",
		width: `${width}px`,
	};
}

function apply_seat_dialog_size(dialog, dialog_layout) {
	dialog.$wrapper.find(".modal-dialog").css({
		"max-width": dialog_layout.width,
		width: dialog_layout.width,
	});
}

function refresh_seat_dialog_summary(dialog, selected_seats, max_seats) {
	dialog.fields_dict.seat_summary.$wrapper.html(`
		<div class="seat-summary">
			<span class="seat-count">${__("Selected")}: ${selected_seats.size}/${max_seats}</span>
			<span class="seat-legend"><span class="seat-legend-dot" style="background:#2f9e44"></span>${__("Available")}</span>
			<span class="seat-legend"><span class="seat-legend-dot" style="background:#1c7ed6"></span>${__("Selected")}</span>
			<span class="seat-legend"><span class="seat-legend-dot" style="background:#c92a2a"></span>${__("Booked")}</span>
		</div>
	`);
}

function populate_selected_seats(frm, selected_seats, existing_seat_prices) {
	frm.clear_table("seats");

	[...selected_seats].sort(sort_seat_labels).forEach((seat_label) => {
		const [row_letter, seat_number] = seat_label.split("-");
		const row = frm.add_child("seats");
		row.seat_label = seat_label;
		row.row_letter = row_letter;
		row.seat_number = cint(seat_number);
		row.seat_price = existing_seat_prices[seat_label] || frm.doc.price_per_seat;
	});

	frm.refresh_field("seats");
	calculate_booking_total(frm);
}

function get_existing_seat_prices(frm) {
	const prices = {};

	(frm.doc.seats || []).forEach((seat) => {
		if (seat.seat_label && seat.seat_price) {
			prices[seat.seat_label] = seat.seat_price;
		}
	});

	return prices;
}

function calculate_booking_total(frm) {
	const seats = frm.doc.seats || [];
	const number_of_seats = seats.length;
	const total_amount = seats.reduce((total, seat) => total + flt(seat.seat_price), 0);

	frm.set_value("number_of_seats", number_of_seats);
	frm.set_value("total_amount", total_amount);
}

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

function row_number_to_letter(row_number) {
	let letter = "";

	while (row_number > 0) {
		row_number--;
		letter = String.fromCharCode(65 + (row_number % 26)) + letter;
		row_number = Math.floor(row_number / 26);
	}

	return letter;
}

function sort_seat_labels(left, right) {
	const [left_row, left_number] = left.split("-");
	const [right_row, right_number] = right.split("-");

	if (left_row === right_row) {
		return cint(left_number) - cint(right_number);
	}

	return left_row.localeCompare(right_row);
}

function show_qr_code(frm) {
	if (frm.doc.docstatus !== 1) return;

	// Find QR attachment
	const attachments = frm.attachments?.get_attachments() || [];
	const qr_file = attachments.find((a) => a.file_name && a.file_name.includes("-qr"));

	if (!qr_file) return;

	const wrapper = frm.fields_dict.seats.$wrapper;

	// Remove old QR display if any
	wrapper.parent().find(".booking-qr-section").remove();

	$(
		`<div class="booking-qr-section" style="margin: 20px 0; text-align: center; padding: 16px; border: 1px solid var(--border-color); border-radius: 8px; background: var(--card-bg);">
			<div style="font-weight: 600; margin-bottom: 8px;">Booking QR Code</div>
			<img src="${qr_file.file_url}" alt="QR Code" style="width: 200px; height: 200px;">
			<div style="margin-top: 8px; font-size: 0.8rem; color: var(--text-muted);">
				Show this at the cinema entrance
			</div>
		</div>`
	).insertAfter(wrapper);
}
