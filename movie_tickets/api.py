import re

import frappe
from frappe import _
from frappe.utils import cint, escape_html, fmt_money, today


BOOKED_SEAT_STATUSES = ("Pending", "Confirmed")
DEFAULT_BOOKING_EXPIRY_MINUTES = 15


@frappe.whitelist()
def get_seat_availability(show_name):
	if not show_name:
		frappe.throw(_("Show is required"))

	show = frappe.db.get_value("Show", show_name, "screen", as_dict=True)
	if not show:
		frappe.throw(_("Show {0} not found").format(show_name))

	screen = frappe.db.get_value(
		"Screen", show.screen, ["seat_rows", "seats_per_row"], as_dict=True
	)
	if not screen:
		frappe.throw(_("Screen {0} not found").format(show.screen))

	seat_rows = cint(screen.seat_rows)
	seats_per_row = cint(screen.seats_per_row)
	booked_seats = set(get_booked_seat_labels(show_name))

	return {
		"total_rows": seat_rows,
		"seats_per_row": seats_per_row,
		"seats": build_seat_map(seat_rows, seats_per_row, booked_seats),
	}


@frappe.whitelist(allow_guest=False)
def create_booking(show, customer_name, customer_email, customer_phone, seats):
	if not show:
		frappe.throw(_("Show is required"))

	seat_rows = normalize_booking_seats(seats)
	if not seat_rows:
		frappe.throw(_("At least one seat must be selected"))

	lock_show(show)
	validate_requested_seats_are_available(show, seat_rows)

	booking = frappe.get_doc(
		doctype="Ticket Booking",
		show=show,
		customer_name=customer_name,
		customer_email=customer_email,
		customer_phone=customer_phone,
	)

	for seat in seat_rows:
		booking.append("seats", seat)

	booking.insert()

	booking_expiry_minutes = get_booking_expiry_minutes()
	return {
		"success": True,
		"booking_name": booking.name,
		"total_amount": booking.total_amount,
		"message": _("Booking created. Complete payment within {0} minutes.").format(
			booking_expiry_minutes
		),
	}


@frappe.whitelist(allow_guest=True)
def get_shows_for_movie(movie, city=None, date=None):
	if not movie:
		frappe.throw(_("Movie is required"))

	conditions = [
		"s.movie = %(movie)s",
		"s.show_date >= %(today)s",
		"s.show_status in ('Scheduled', 'Now Playing')",
	]
	values = {"movie": movie, "today": today()}

	if city:
		conditions.append("theater.city = %(city)s")
		values["city"] = city

	if date:
		conditions.append("s.show_date = %(date)s")
		values["date"] = date

	return frappe.db.sql(
		f"""
		select
			s.name as show_name,
			s.theater,
			s.screen,
			screen.screen_type,
			s.show_date,
			s.start_time,
			s.ticket_price,
			s.available_seats
		from `tabShow` s
		inner join `tabScreen` screen on screen.name = s.screen
		inner join `tabTheater` theater on theater.name = s.theater
		where {' and '.join(conditions)}
		order by s.show_date asc, s.start_time asc, s.theater asc
		""",
		values,
		as_dict=True,
	)


@frappe.whitelist()
def send_booking_confirmation(booking_name):
	if not booking_name:
		frappe.throw(_("Booking is required"))

	booking = frappe.get_doc("Ticket Booking", booking_name)
	booking.check_permission("read")

	if not booking.customer_email:
		frappe.throw(_("Customer email is required to send booking confirmation"))

	frappe.sendmail(
		recipients=[booking.customer_email],
		subject=_("Booking Confirmation - {0}").format(booking.name),
		message=build_booking_confirmation_html(booking),
	)

	return {
		"success": True,
		"booking_name": booking.name,
		"message": _("Booking confirmation sent"),
	}


def get_booked_seat_labels(show_name):
	return frappe.db.sql_list(
		"""
		select distinct seat.seat_label
		from `tabTicket Booking` booking
		inner join `tabBooked Seat` seat
			on seat.parent = booking.name
			and seat.parenttype = 'Ticket Booking'
		where booking.show = %s
			and booking.docstatus != 2
			and booking.booking_status in %s
		""",
		(show_name, BOOKED_SEAT_STATUSES),
	)


def get_booking_expiry_minutes():
	return (
		cint(frappe.db.get_single_value("Booking Configuration", "booking_expiry_minutes"))
		or DEFAULT_BOOKING_EXPIRY_MINUTES
	)


def build_booking_confirmation_html(booking):
	seats = ", ".join(seat.seat_label for seat in booking.seats) or "-"
	show_time = f"{booking.show_date or '-'} {format_time_value(booking.start_time)}"
	amount = fmt_money(booking.total_amount or 0)

	return f"""
		<div style="font-family: Arial, sans-serif; line-height: 1.5; color: #1f2933;">
			<h2 style="margin: 0 0 12px;">{escape_html(_('Booking Confirmation'))}</h2>
			<p>{escape_html(_('Your movie ticket booking has been created.'))}</p>
			<table style="border-collapse: collapse; width: 100%; max-width: 640px;">
				{booking_detail_row(_('Booking ID'), booking.name)}
				{booking_detail_row(_('Movie'), booking.movie_title)}
				{booking_detail_row(_('Theater'), booking.theater)}
				{booking_detail_row(_('Screen'), booking.screen)}
				{booking_detail_row(_('Show Time'), show_time)}
				{booking_detail_row(_('Seats'), seats)}
				{booking_detail_row(_('Amount'), amount)}
			</table>
		</div>
	"""


def booking_detail_row(label, value):
	return f"""
		<tr>
			<td style="border: 1px solid #d8dfe5; padding: 8px; font-weight: 600; width: 160px;">
				{escape_html(label)}
			</td>
			<td style="border: 1px solid #d8dfe5; padding: 8px;">
				{escape_html(value or '-')}
			</td>
		</tr>
	"""


def format_time_value(value):
	if not value:
		return "-"

	return str(value)


def normalize_booking_seats(seats):
	if isinstance(seats, str):
		seats = frappe.parse_json(seats)

	normalized_seats = []
	for seat in seats or []:
		seat_label = seat.get("seat_label") if isinstance(seat, dict) else seat
		row_letter, seat_number = parse_seat_label(seat_label)

		normalized_seats.append(
			{
				"seat_label": seat_label,
				"row_letter": row_letter,
				"seat_number": seat_number,
			}
		)

	return normalized_seats


def parse_seat_label(seat_label):
	match = re.fullmatch(r"([A-Z]+)-(\d+)", seat_label or "")
	if not match:
		frappe.throw(_("Seat label must be in the format {0}").format("A-12"))

	return match.group(1), int(match.group(2))


def lock_show(show):
	if hasattr(frappe, "lock_doc"):
		frappe.lock_doc("Show", show)
		return frappe.get_doc("Show", show)

	return frappe.get_doc("Show", show, for_update=True)


def validate_requested_seats_are_available(show, seats):
	booked_seats = set(get_booked_seat_labels(show))
	for seat in seats:
		if seat["seat_label"] in booked_seats:
			frappe.throw(_("Seat {0} is already booked for this show.").format(seat["seat_label"]))


def build_seat_map(seat_rows, seats_per_row, booked_seats):
	seat_map = []

	for row_number in range(1, seat_rows + 1):
		row_label = row_number_to_letter(row_number)
		row = []

		for seat_number in range(1, seats_per_row + 1):
			seat_label = f"{row_label}-{seat_number}"
			row.append(
				{
					"seat_label": seat_label,
					"status": "booked" if seat_label in booked_seats else "available",
				}
			)

		seat_map.append(row)

	return seat_map


def row_number_to_letter(row_number):
	letter = ""

	while row_number > 0:
		row_number -= 1
		letter = chr(65 + (row_number % 26)) + letter
		row_number //= 26

	return letter
