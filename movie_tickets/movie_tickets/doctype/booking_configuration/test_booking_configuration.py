from frappe.tests import IntegrationTestCase

from movie_tickets.movie_tickets.doctype.booking_configuration.booking_configuration import (
	get_booking_configuration,
)


class TestBookingConfiguration(IntegrationTestCase):
	def test_booking_configuration_defaults(self):
		configuration = get_booking_configuration()

		self.assertEqual(configuration.max_seats_per_booking, 10)
		self.assertEqual(configuration.booking_expiry_minutes, 15)
		self.assertEqual(configuration.full_refund_hours, 4)
		self.assertEqual(configuration.partial_refund_hours, 2)
		self.assertEqual(configuration.partial_refund_pct, 50)
		self.assertEqual(configuration.enable_auto_expiry, 1)
		self.assertEqual(configuration.booking_open_days_before, 7)