import frappe
from frappe.tests import IntegrationTestCase


TEST_THEATER = "Screen Test Cinema - Ahmedabad"


class TestScreen(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Theater", TEST_THEATER):
			frappe.get_doc(
				doctype="Theater",
				theater_name="Screen Test Cinema",
				city="Ahmedabad",
				address="CG Road, Ahmedabad",
			).insert()

	def tearDown(self):
		frappe.db.delete("Screen", {"theater": TEST_THEATER})
		frappe.db.delete("Theater", {"name": TEST_THEATER})

	def test_screen_name_uses_theater_and_screen_name(self):
		screen = make_screen().insert()

		self.assertEqual(screen.name, "Screen Test Cinema - Ahmedabad-Screen 1")

	def test_total_seats_must_match_rows_times_seats_per_row(self):
		screen = make_screen(total_seats=149)

		self.assertRaises(frappe.ValidationError, screen.insert)

	def test_theater_total_screens_updates_on_save(self):
		make_screen(screen_name="Screen 1").insert()
		make_screen(screen_name="Screen 2").insert()

		self.assertEqual(frappe.db.get_value("Theater", TEST_THEATER, "total_screens"), 2)


def make_screen(**kwargs):
	screen = frappe.get_doc(
		doctype="Screen",
		screen_name="Screen 1",
		theater=TEST_THEATER,
		total_seats=150,
		seat_rows=10,
		seats_per_row=15,
		base_price=250,
	)
	screen.update(kwargs)
	return screen