import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt


class BookingConfiguration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		booking_expiry_minutes: DF.Int
		booking_open_days_before: DF.Int
		enable_auto_expiry: DF.Check
		full_refund_hours: DF.Float
		max_seats_per_booking: DF.Int
		partial_refund_hours: DF.Float
		partial_refund_pct: DF.Float
	# end: auto-generated types

	pass


DEFAULT_BOOKING_CONFIGURATION = {
	"max_seats_per_booking": 10,
	"booking_expiry_minutes": 15,
	"full_refund_hours": 4,
	"partial_refund_hours": 2,
	"partial_refund_pct": 50,
	"enable_auto_expiry": 1,
	"booking_open_days_before": 7,
}


def get_booking_configuration():
	configuration = DEFAULT_BOOKING_CONFIGURATION.copy()
	values = frappe.db.get_singles_dict("Booking Configuration")

	for fieldname, default_value in DEFAULT_BOOKING_CONFIGURATION.items():
		value = values.get(fieldname)
		configuration[fieldname] = get_configuration_value(value, default_value)

	return frappe._dict(configuration)


def get_configuration_value(value, default_value):
	if value in (None, ""):
		return default_value

	if isinstance(default_value, float):
		return flt(value)

	return cint(value)