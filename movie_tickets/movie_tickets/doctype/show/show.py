import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time, getdate, now_datetime, today


class Show(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		available_seats: DF.Int
		booked_seats: DF.Int
		end_time: DF.Time | None
		movie: DF.Link
		movie_title: DF.Data | None
		naming_series: DF.Literal["SHW-.YYYY.-.#####"]
		screen: DF.Link
		show_date: DF.Date
		show_status: DF.Literal["Scheduled", "Now Playing", "Completed", "Cancelled"]
		start_time: DF.Time
		theater: DF.Link
		ticket_price: DF.Currency
		total_seats: DF.Int
	# end: auto-generated types

	def before_insert(self):
		self.set_show_details()

	def validate(self):
		self.set_show_details()
		self.validate_show_date()
		self.validate_movie_is_not_ended()
		self.validate_showtime_conflicts()

	def on_update(self):
		self.cancel_linked_bookings()

	def set_show_details(self):
		self.set_movie_details()
		self.set_screen_details()
		self.set_end_time()
		self.set_available_seats()

	def set_movie_details(self):
		if not self.movie:
			return

		self.movie_title = frappe.db.get_value("Movie", self.movie, "title")

	def set_screen_details(self):
		if not self.screen:
			return

		screen = frappe.db.get_value("Screen", self.screen, ["theater", "total_seats", "base_price"], as_dict=True)
		if not screen:
			return

		self.theater = screen.theater
		self.total_seats = screen.total_seats

		if not self.ticket_price:
			self.ticket_price = screen.base_price

	def set_end_time(self):
		if not self.movie or not self.start_time:
			return

		duration_minutes = frappe.db.get_value("Movie", self.movie, "duration_minutes")
		if duration_minutes is None:
			return

		start_time = get_time(self.start_time)
		start_datetime = datetime.datetime.combine(datetime.date.today(), start_time)
		end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)
		self.end_time = end_datetime.time().strftime("%H:%M:%S")

	def set_available_seats(self):
		if not self.is_new() or self.available_seats is not None:
			return

		self.booked_seats = self.booked_seats or 0
		self.available_seats = self.total_seats

	def validate_show_date(self):
		if self.show_date and getdate(self.show_date) < getdate(today()):
			frappe.throw(_("Show Date cannot be in the past"))

	def validate_movie_is_not_ended(self):
		if not self.movie:
			return

		movie_status = frappe.db.get_value("Movie", self.movie, "movie_status")
		if movie_status == "Ended":
			frappe.throw(_("Movie {0} has ended").format(frappe.bold(self.movie_title or self.movie)))

	def validate_showtime_conflicts(self):
		if not self.screen or not self.show_date or not self.start_time or not self.end_time:
			return

		show_start, show_end = get_time_window(self.start_time, self.end_time)
		existing_shows = frappe.get_all(
			"Show",
			filters={
				"screen": self.screen,
				"show_date": self.show_date,
				"name": ["!=", self.name or ""],
				"show_status": ["!=", "Cancelled"],
			},
			fields=["name", "start_time", "end_time"],
		)

		for existing_show in existing_shows:
			if not existing_show.start_time or not existing_show.end_time:
				continue

			existing_start, existing_end = get_time_window(existing_show.start_time, existing_show.end_time)
			if show_start < existing_end and show_end > existing_start:
				frappe.throw(
					_("Screen {0} already has a show scheduled from {1} to {2} on {3}.").format(
						self.screen,
						format_show_time(existing_show.start_time),
						format_show_time(existing_show.end_time),
						getdate(self.show_date),
					)
				)

	def cancel_linked_bookings(self):
		previous_doc = self.get_doc_before_save()
		if not previous_doc or previous_doc.show_status == "Cancelled" or self.show_status != "Cancelled":
			return

		bookings = frappe.get_all(
			"Ticket Booking",
			filters={"show": self.name, "booking_status": ["in", ["Pending", "Confirmed"]]},
			fields=["name", "docstatus", "total_amount"],
		)

		for booking in bookings:
			frappe.db.set_value(
				"Ticket Booking",
				booking.name,
				{
					"booking_status": "Cancelled",
					"cancellation_reason": "Show Cancelled",
					"cancellation_time": now_datetime(),
					"refund_amount": booking.total_amount,
					"payment_status": "Refunded",
				},
			)

			if booking.docstatus == 1:
				frappe.get_doc("Ticket Booking", booking.name).cancel()


def get_time_window(start_time, end_time):
	start = datetime.datetime.combine(datetime.date.today(), get_time(start_time))
	end = datetime.datetime.combine(datetime.date.today(), get_time(end_time))

	if end <= start:
		end += datetime.timedelta(days=1)

	return start, end


def format_show_time(show_time):
	return get_time(show_time).strftime("%H:%M:%S")


def update_show_statuses():
	"""Hourly: update show_status based on current date/time."""
	now = now_datetime()
	current_date = now.date()
	current_time = now.time().strftime("%H:%M:%S")

	# Past-date Scheduled/Now Playing shows → Completed
	frappe.db.sql("""
		UPDATE `tabShow`
		SET show_status = 'Completed'
		WHERE show_date < %s
			AND show_status IN ('Scheduled', 'Now Playing')
	""", (current_date,))

	# Today's shows where end_time has passed → Completed
	frappe.db.sql("""
		UPDATE `tabShow`
		SET show_status = 'Completed'
		WHERE show_date = %s
			AND end_time IS NOT NULL
			AND end_time <= %s
			AND show_status IN ('Scheduled', 'Now Playing')
	""", (current_date, current_time))

	# Today's shows where start_time passed but end_time not yet → Now Playing
	frappe.db.sql("""
		UPDATE `tabShow`
		SET show_status = 'Now Playing'
		WHERE show_date = %s
			AND start_time <= %s
			AND (end_time IS NULL OR end_time > %s)
			AND show_status = 'Scheduled'
	""", (current_date, current_time, current_time))

	frappe.db.commit()