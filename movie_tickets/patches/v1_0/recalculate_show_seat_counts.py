import frappe


def execute():
	"""Recalculate booked_seats and available_seats for all Shows
	by counting actual Confirmed bookings (docstatus=1, booking_status='Confirmed')."""

	shows = frappe.db.sql(
		"""
		SELECT
			s.name,
			s.total_seats,
			IFNULL(SUM(tb.number_of_seats), 0) AS actual_booked
		FROM `tabShow` s
		LEFT JOIN `tabTicket Booking` tb
			ON tb.show = s.name
			AND tb.docstatus = 1
			AND tb.booking_status = 'Confirmed'
		GROUP BY s.name, s.total_seats
		""",
		as_dict=True,
	)

	for show in shows:
		booked = show.actual_booked
		available = max(show.total_seats - booked, 0)

		frappe.db.set_value(
			"Show",
			show.name,
			{"booked_seats": booked, "available_seats": available},
			update_modified=False,
		)

	frappe.db.commit()
	frappe.msgprint(f"Recalculated seat counts for {len(shows)} shows.")
