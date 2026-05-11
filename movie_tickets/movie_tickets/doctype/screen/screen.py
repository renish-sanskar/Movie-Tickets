import frappe
from frappe import _
from frappe.model.document import Document


class Screen(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_price: DF.Currency
		is_active: DF.Check
		screen_name: DF.Data
		screen_type: DF.Literal["Standard", "IMAX", "3D", "4DX"]
		seat_rows: DF.Int
		seats_per_row: DF.Int
		theater: DF.Link
		total_seats: DF.Int
	# end: auto-generated types

	def autoname(self):
		self.name = f"{self.theater.strip()}-{self.screen_name.strip()}"

	def validate(self):
		self.validate_total_seats()

	def after_insert(self):
		update_theater_total_screens(self.theater)

	def on_update(self):
		self.update_linked_theater_total_screens()

	def on_trash(self):
		update_theater_total_screens(self.theater)

	def validate_total_seats(self):
		expected_total_seats = self.seat_rows * self.seats_per_row

		if self.total_seats != expected_total_seats:
			frappe.throw(
				_("Total Seats must equal Seat Rows x Seats Per Row ({0})").format(expected_total_seats)
			)

	def update_linked_theater_total_screens(self):
		previous_doc = self.get_doc_before_save()
		previous_theater = previous_doc.theater if previous_doc else None

		for theater in {previous_theater, self.theater}:
			update_theater_total_screens(theater)


def update_theater_total_screens(theater):
	if not theater:
		return

	total_screens = frappe.db.count("Screen", {"theater": theater})
	frappe.db.set_value("Theater", theater, "total_screens", total_screens)