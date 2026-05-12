import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, get_time, now_datetime

from movie_tickets.movie_tickets.doctype.booking_configuration.booking_configuration import (
	get_booking_configuration,
)

VALID_SHOW_STATUSES_FOR_BOOKING = ("Scheduled", "Now Playing")
BOOKED_SEAT_STATUSES = ("Pending", "Confirmed")
CINEMA_MANAGER_ROLES = ("System Manager", "Cinema Manager", "Box Office Staff")


class TicketBooking(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from movie_tickets.movie_tickets.doctype.booked_seat.booked_seat import BookedSeat

		booked_by: DF.Link | None
		booking_status: DF.Literal["Pending", "Confirmed", "Cancelled", "Expired"]
		booking_time: DF.Datetime | None
		cancellation_reason: DF.SmallText | None
		cancellation_time: DF.Datetime | None
		customer_email: DF.Data
		customer_name: DF.Data
		customer_phone: DF.Data
		movie_title: DF.Data | None
		naming_series: DF.Literal["BKG-.YYYY.-.#####"]
		number_of_seats: DF.Int
		payment_status: DF.Literal["Unpaid", "Paid", "Refunded"]
		price_per_seat: DF.Currency
		refund_amount: DF.Currency
		screen: DF.Data | None
		seats: DF.Table[BookedSeat]
		show: DF.Link
		show_date: DF.Date | None
		start_time: DF.Time | None
		theater: DF.Data | None
		total_amount: DF.Currency
	# end: auto-generated types

	def has_permission(self, ptype="read", user=None):
		user = user or frappe.session.user

		if user == "Administrator" or set(frappe.get_roles(user)).intersection(CINEMA_MANAGER_ROLES):
			return True

		if "Customer" in frappe.get_roles(user):
			if ptype == "create":
				return True

			if ptype in ("read", "write", "print", "email", "submit"):
				return self.booked_by == user

			return False

		return False

	def validate(self):
		self.set_booking_details()
		self.set_booking_defaults()
		self.set_seat_prices()
		self.set_totals()
		self.validate_show_status()
		self.validate_number_of_seats()
		self.validate_seat_labels()
		self.validate_duplicate_seats()
		self.validate_seats_are_available()

	def on_submit(self):
		self.booking_status = "Confirmed"
		self.payment_status = "Paid"
		self.db_set({"booking_status": "Confirmed", "payment_status": "Paid"})
		update_show_seat_counts(self.show, self.number_of_seats)

	def on_cancel(self):
		refund_amount, payment_status = self.get_cancellation_refund()
		self.booking_status = "Cancelled"
		self.refund_amount = refund_amount
		self.payment_status = payment_status
		self.cancellation_time = now_datetime()
		self.db_set(
			{
				"booking_status": self.booking_status,
				"refund_amount": self.refund_amount,
				"payment_status": self.payment_status,
				"cancellation_time": self.cancellation_time,
			}
		)
		update_show_seat_counts(self.show, -self.number_of_seats)

	def set_booking_details(self):
		if not self.show:
			return

		show = frappe.db.get_value(
			"Show",
			self.show,
			["movie_title", "theater", "screen", "show_date", "start_time", "ticket_price"],
			as_dict=True,
		)
		if not show:
			return

		self.movie_title = show.movie_title
		self.theater = show.theater
		self.screen = show.screen
		self.show_date = show.show_date
		self.start_time = show.start_time
		self.price_per_seat = show.ticket_price

	def set_booking_defaults(self):
		self.booked_by = self.booked_by or frappe.session.user

		if self.is_new() and not self.booking_time:
			self.booking_time = now_datetime()

	def set_seat_prices(self):
		for seat in self.seats:
			if not seat.seat_price:
				seat.seat_price = self.price_per_seat

	def set_totals(self):
		self.number_of_seats = len(self.seats)
		self.total_amount = sum(flt(seat.seat_price) for seat in self.seats)

	def validate_show_status(self):
		show_status = frappe.db.get_value("Show", self.show, "show_status")
		if show_status not in VALID_SHOW_STATUSES_FOR_BOOKING:
			frappe.throw(_("Cannot book tickets for a {0} show.").format(show_status))

	def validate_number_of_seats(self):
		configuration = get_booking_configuration()
		max_seats_per_booking = configuration.max_seats_per_booking

		if self.number_of_seats < 1:
			frappe.throw(_("At least one seat must be selected"))

		if self.number_of_seats > max_seats_per_booking:
			frappe.throw(
				_("Cannot book more than {0} tickets at a time").format(max_seats_per_booking)
			)

	def validate_seat_labels(self):
		screen = frappe.db.get_value("Screen", self.screen, ["seat_rows", "seats_per_row"], as_dict=True)
		if not screen:
			return

		for seat in self.seats:
			row_letter, seat_number = parse_seat_label(seat.seat_label)

			if row_letter != seat.row_letter or seat_number != seat.seat_number:
				frappe.throw(_("Seat {0} does not match row letter and seat number").format(seat.seat_label))

			if row_letter_to_number(row_letter) > screen.seat_rows or seat_number > screen.seats_per_row:
				frappe.throw(_("Seat {0} is outside the screen seating layout").format(seat.seat_label))

	def validate_duplicate_seats(self):
		seen_seats = set()
		for seat in self.seats:
			if seat.seat_label in seen_seats:
				frappe.throw(_("Duplicate seat {0} in this booking").format(seat.seat_label))

			seen_seats.add(seat.seat_label)

	def validate_seats_are_available(self):
		for seat in self.seats:
			if is_seat_booked(self.show, seat.seat_label, self.name):
				frappe.throw(_("Seat {0} is already booked for this show.").format(seat.seat_label))

	def get_cancellation_refund(self):
		configuration = get_booking_configuration()
		show = frappe.db.get_value("Show", self.show, ["show_date", "start_time"], as_dict=True)
		if not show:
			return 0, "Unpaid"

		show_start = get_datetime(f"{show.show_date} {get_time(show.start_time)}")
		hours_until_show = (show_start - now_datetime()).total_seconds() / 3600

		if hours_until_show > configuration.full_refund_hours:
			return self.total_amount, "Refunded"

		if hours_until_show >= configuration.partial_refund_hours:
			return self.total_amount * (configuration.partial_refund_pct / 100), "Refunded"

		return 0, self.payment_status


def is_seat_booked(show, seat_label, booking_name):
	return frappe.db.sql(
		"""
		select booking.name
		from `tabTicket Booking` booking
		inner join `tabBooked Seat` seat
			on seat.parent = booking.name
			and seat.parenttype = 'Ticket Booking'
		where booking.show = %s
			and booking.name != %s
			and booking.docstatus != 2
			and booking.booking_status in ('Pending', 'Confirmed')
			and seat.seat_label = %s
		limit 1
		""",
		(show, booking_name or "", seat_label),
	)


def parse_seat_label(seat_label):
	match = re.fullmatch(r"([A-Z]+)-(\d+)", seat_label or "")
	if not match:
		frappe.throw(_("Seat label must be in the format {0}").format("A-12"))

	return match.group(1), int(match.group(2))


def row_letter_to_number(row_letter):
	row_number = 0
	for character in row_letter:
		row_number = row_number * 26 + ord(character) - ord("A") + 1

	return row_number


def update_show_seat_counts(show, seat_count):
	if not show or not seat_count:
		return

	show_doc = frappe.get_doc("Show", show)
	show_doc.booked_seats = (show_doc.booked_seats or 0) + seat_count
	show_doc.available_seats = (show_doc.available_seats or 0) - seat_count
	show_doc.db_set(
		{
			"booked_seats": show_doc.booked_seats,
			"available_seats": show_doc.available_seats,
		}
	)


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user

	if user == "Administrator" or set(frappe.get_roles(user)).intersection(CINEMA_MANAGER_ROLES):
		return ""

	if "Customer" in frappe.get_roles(user):
		return "`tabTicket Booking`.booked_by = {0}".format(frappe.db.escape(user))

	return "1 = 0"


@frappe.whitelist()
def get_booked_seats(show, booking=None):
	if not show:
		return []

	return frappe.db.sql_list(
		"""
		select distinct seat.seat_label
		from `tabTicket Booking` booking
		inner join `tabBooked Seat` seat
			on seat.parent = booking.name
			and seat.parenttype = 'Ticket Booking'
		where booking.show = %s
			and booking.name != %s
			and booking.docstatus != 2
			and booking.booking_status in ('Pending', 'Confirmed')
		""",
		(show, booking or ""),
	)


@frappe.whitelist()
def get_screen_layout(screen):
	"""Return seat_rows and seats_per_row for a screen without requiring Screen read permission."""
	if not screen or not frappe.db.exists("Screen", screen):
		frappe.throw(_("Screen not found"))
	row = frappe.db.get_value("Screen", screen, ["seat_rows", "seats_per_row"], as_dict=True)
	return row


@frappe.whitelist()
def get_max_seats_per_booking():
	return get_booking_configuration().max_seats_per_booking


@frappe.whitelist()
def send_booking_confirmation(booking):
	frappe.get_doc("Ticket Booking", booking).check_permission("read")
	return {"message": _("Booking confirmation sent")}