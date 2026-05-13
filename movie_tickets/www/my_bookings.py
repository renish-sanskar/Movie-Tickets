import frappe


no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw("Please login to view your bookings", frappe.PermissionError)

	context.title = "My Bookings"

	bookings = frappe.get_all(
		"Ticket Booking",
		filters={"booked_by": frappe.session.user},
		fields=[
			"name", "movie_title", "show", "show_date", "start_time",
			"number_of_seats", "total_amount", "booking_status", "creation",
			"theater",
		],
		order_by="creation desc",
	)

	for booking in bookings:
		booking.show_time_formatted = frappe.utils.format_time(booking.start_time, "hh:mm a") if booking.start_time else ""
		booking.show_date_formatted = frappe.utils.formatdate(booking.show_date, "d MMM yyyy") if booking.show_date else ""

		seats = frappe.get_all(
			"Booked Seat",
			filters={"parent": booking.name},
			fields=["seat_label"],
			order_by="seat_label asc",
			pluck="seat_label",
		)
		booking.seat_labels = ", ".join(seats) if seats else ""

	context.bookings = bookings
