import frappe


def execute():
	"""Set custom_booking_source = 'Counter' for all existing bookings where the field is NULL."""

	count = frappe.db.sql(
		"""
		UPDATE `tabTicket Booking`
		SET custom_booking_source = 'Counter'
		WHERE custom_booking_source IS NULL OR custom_booking_source = ''
		""",
	)

	affected = frappe.db.sql("SELECT ROW_COUNT() AS cnt")[0][0]
	frappe.db.commit()
	frappe.msgprint(f"Updated {affected} bookings with booking_source = 'Counter'.")
