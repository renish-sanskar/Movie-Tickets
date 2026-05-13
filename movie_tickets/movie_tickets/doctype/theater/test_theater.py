import frappe
from frappe.tests import IntegrationTestCase


class TestTheater(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Theater", {"name": "PVR - Ahmedabad"})

	def test_theater_name_uses_city_suffix(self):
		theater = make_theater().insert()

		self.assertEqual(theater.name, "PVR - Ahmedabad")

	def test_total_screens_defaults_to_zero_without_screen_links(self):
		theater = make_theater().insert()

		self.assertEqual(theater.total_screens, 0)


def make_theater(**kwargs):
	theater = frappe.get_doc(
		doctype="Theater",
		theater_name="PVR",
		city="Ahmedabad",
		address="CG Road, Ahmedabad",
	)
	theater.update(kwargs)
	return theater