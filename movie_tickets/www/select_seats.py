import frappe
from frappe import _
from frappe.utils import fmt_money, format_time, formatdate

no_cache = True


def get_context(context):
	show_name = frappe.form_dict.get("show")
	if not show_name:
		frappe.throw(_("Show is required"), frappe.DoesNotExistError)

	show = frappe.db.get_value(
		"Show",
		show_name,
		[
			"name",
			"movie",
			"movie_title",
			"theater",
			"screen",
			"show_date",
			"start_time",
			"end_time",
			"ticket_price",
			"total_seats",
			"available_seats",
			"show_status",
		],
		as_dict=True,
	)

	if not show:
		frappe.throw(_("Show {0} not found").format(show_name), frappe.DoesNotExistError)

	if show.show_status not in ("Scheduled", "Now Playing"):
		frappe.throw(_("This show is no longer available for booking."))

	movie = frappe.db.get_value(
		"Movie",
		show.movie,
		["title", "genre", "language", "duration_minutes", "rating", "poster"],
		as_dict=True,
	)

	screen = frappe.db.get_value(
		"Screen",
		show.screen,
		["screen_name", "screen_type", "seat_rows", "seats_per_row"],
		as_dict=True,
	)

	max_seats = frappe.db.get_single_value("Booking Configuration", "max_seats_per_booking") or 10

	context.show = show
	context.show_name = show.name
	context.movie = movie or {}
	context.screen = screen or {}
	context.max_seats = int(max_seats)
	context.seat_rows = int(screen.seat_rows) if screen else 0
	context.seats_per_row = int(screen.seats_per_row) if screen else 0
	context.ticket_price = show.ticket_price or 0
	context.ticket_price_formatted = fmt_money(show.ticket_price or 0, currency="INR")
	context.show_date_formatted = formatdate(show.show_date, "EEE, d MMM yyyy")
	context.show_time_formatted = format_time(show.start_time, "hh:mm a") if show.start_time else ""
	context.is_logged_in = frappe.session.user != "Guest"
	context.title = f"Select Seats - {movie.title}" if movie else "Select Seats"
	context.no_cache = True
