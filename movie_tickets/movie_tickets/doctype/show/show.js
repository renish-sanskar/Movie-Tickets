frappe.ui.form.on("Show", {
	refresh(frm) {
		add_view_bookings_button(frm);
		show_dashboard_indicators(frm);
	},

	movie(frm) {
		show_calculated_end_time(frm);
	},

	screen(frm) {
		set_ticket_price_from_screen(frm);
	},

	start_time(frm) {
		show_calculated_end_time(frm);
	},
});

function add_view_bookings_button(frm) {
	if (frm.is_new()) {
		return;
	}

	frm.add_custom_button(__("View Bookings"), () => {
		frappe.route_options = {
			show: frm.doc.name,
		};
		frappe.set_route("List", "Ticket Booking");
	});
}

function show_dashboard_indicators(frm) {
	if (frm.is_new()) {
		return;
	}

	frm.dashboard.clear_headline();
	frm.dashboard.clear_indicator();

	const booked_seats = cint(frm.doc.booked_seats);
	const available_seats = cint(frm.doc.available_seats);
	const total_seats = cint(frm.doc.total_seats) || booked_seats + available_seats;
	const occupancy = total_seats ? (booked_seats / total_seats) * 100 : 0;
	let occupancy_indicator = "orange";

	if (occupancy >= 100) {
		occupancy_indicator = "red";
	}

	frm.dashboard.add_indicator(__("Booked: {0}", [booked_seats]), "blue");
	frm.dashboard.add_indicator(__("Available: {0}", [available_seats]), "green");
	frm.dashboard.add_indicator(
		__("Occupancy: {0}%", [flt(occupancy, 2)]),
		occupancy_indicator
	);
}

function show_calculated_end_time(frm) {
	if (!frm.doc.movie) {
		return;
	}

	const selected_movie = frm.doc.movie;

	frappe.db.get_value("Movie", selected_movie, "duration_minutes").then((response) => {
		if (frm.doc.movie !== selected_movie) {
			return;
		}

		const duration_minutes = cint(response.message?.duration_minutes);

		if (!duration_minutes || !frm.doc.start_time) {
			return;
		}

		const end_time = calculate_end_time(frm.doc.start_time, duration_minutes);

		if (!end_time) {
			return;
		}

		frm.set_value("end_time", end_time);
		frappe.show_alert({
			message: __("Calculated End Time: {0}", [end_time]),
			indicator: "blue",
		});
	});
}

function calculate_end_time(start_time, duration_minutes) {
	const [hours, minutes, seconds = 0] = String(start_time).split(":").map(cint);

	if (hours === undefined || minutes === undefined) {
		return null;
	}

	const end_time = new Date();
	end_time.setHours(hours, minutes, seconds, 0);
	end_time.setMinutes(end_time.getMinutes() + duration_minutes);

	return [end_time.getHours(), end_time.getMinutes(), end_time.getSeconds()]
		.map((value) => String(value).padStart(2, "0"))
		.join(":");
}

function set_ticket_price_from_screen(frm) {
	if (!frm.doc.screen) {
		return;
	}

	frappe.db.get_value("Screen", frm.doc.screen, "base_price").then((response) => {
		const base_price = response.message?.base_price;

		if (base_price !== undefined && base_price !== null) {
			frm.set_value("ticket_price", base_price);
		}
	});
}
