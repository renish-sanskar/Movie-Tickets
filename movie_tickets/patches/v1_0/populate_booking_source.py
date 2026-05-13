import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def ensure_booking_source_field():
	create_custom_fields(
		{
			"Ticket Booking": [
				{
					"fieldname": "custom_booking_source",
					"label": "Booking Source",
					"fieldtype": "Select",
					"insert_after": "booked_by",
					"options": "Counter\nWebsite\nApp",
					"default": "Website",
					"module": "Movie Tickets",
				}
			]
		},
		ignore_validate=True,
	)

	if not frappe.db.has_column("Ticket Booking", "custom_booking_source"):
		frappe.clear_cache(doctype="Ticket Booking")
		frappe.db.updatedb("Ticket Booking")


def execute():
	"""Set custom_booking_source = 'Counter' for all existing bookings where the field is NULL."""

	ensure_booking_source_field()

	frappe.db.sql(
		"""
		UPDATE `tabTicket Booking`
		SET custom_booking_source = 'Counter'
		WHERE custom_booking_source IS NULL OR custom_booking_source = ''
		""",
	)

	affected = frappe.db.sql("SELECT ROW_COUNT() AS cnt")[0][0]
	frappe.db.commit()
	frappe.msgprint(f"Updated {affected} bookings with booking_source = 'Counter'.")
