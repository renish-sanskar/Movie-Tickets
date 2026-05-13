import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today


TEST_GENRE = "Show Test Genre"
TEST_MOVIE_TITLE = "Show Test Movie"
TEST_ENDED_MOVIE_TITLE = "Ended Show Test Movie"
TEST_THEATER = "Show Test Theater - Ahmedabad"
TEST_SCREEN = f"{TEST_THEATER}-Screen 1"


class TestShow(IntegrationTestCase):
	def setUp(self):
		cleanup_test_records()
		create_test_records()

	def tearDown(self):
		cleanup_test_records()

	def test_show_defaults_from_movie_and_screen(self):
		show = make_show().insert()

		self.assertEqual(show.movie_title, TEST_MOVIE_TITLE)
		self.assertEqual(show.theater, TEST_THEATER)
		self.assertEqual(show.total_seats, 150)
		self.assertEqual(show.available_seats, 150)
		self.assertEqual(show.booked_seats, 0)
		self.assertEqual(show.ticket_price, 250)

	def test_end_time_is_calculated_from_movie_duration(self):
		show = make_show(start_time="10:30:00").insert()

		self.assertEqual(str(show.end_time), "12:30:00")

	def test_ticket_price_can_be_overridden(self):
		show = make_show(ticket_price=300).insert()

		self.assertEqual(show.ticket_price, 300)

	def test_zero_ticket_price_defaults_from_screen_base_price(self):
		show = make_show(ticket_price=0).insert()

		self.assertEqual(show.ticket_price, 250)

	def test_show_date_cannot_be_in_the_past(self):
		show = make_show(show_date=add_days(today(), -1))

		self.assertRaises(frappe.ValidationError, show.insert)

	def test_movie_cannot_be_ended(self):
		movie = frappe.get_doc(
			doctype="Movie",
			title=TEST_ENDED_MOVIE_TITLE,
			language="English",
			genre=TEST_GENRE,
			duration_minutes=120,
			release_date=add_days(today(), -2),
			end_date=add_days(today(), -1),
		).insert()

		show = make_show(movie=movie.name)

		self.assertRaises(frappe.ValidationError, show.insert)

	def test_showtime_conflicts_on_same_screen_and_date(self):
		make_show(start_time="09:00:00").insert()
		conflicting_show = make_show(start_time="10:00:00")

		self.assertRaises(frappe.ValidationError, conflicting_show.insert)

	def test_cancelled_show_auto_cancels_linked_bookings(self):
		show = make_show().insert()
		booking = make_booking(show.name).insert()

		show.show_status = "Cancelled"
		show.save()

		booking.reload()
		self.assertEqual(booking.booking_status, "Cancelled")
		self.assertEqual(booking.cancellation_reason, "Show Cancelled")
		self.assertEqual(booking.payment_status, "Refunded")
		self.assertEqual(booking.refund_amount, booking.total_amount)
		self.assertTrue(booking.cancellation_time)


def create_test_records():
	frappe.get_doc(doctype="Movie Genre", genre_name=TEST_GENRE).insert()

	frappe.get_doc(
		doctype="Movie",
		title=TEST_MOVIE_TITLE,
		language="English",
		genre=TEST_GENRE,
		duration_minutes=120,
		release_date=today(),
	).insert()

	frappe.get_doc(
		doctype="Theater",
		theater_name="Show Test Theater",
		city="Ahmedabad",
		address="CG Road, Ahmedabad",
	).insert()

	frappe.get_doc(
		doctype="Screen",
		screen_name="Screen 1",
		theater=TEST_THEATER,
		total_seats=150,
		seat_rows=10,
		seats_per_row=15,
		base_price=250,
	).insert()


def make_show(**kwargs):
	show = frappe.get_doc(
		doctype="Show",
		movie=frappe.db.get_value("Movie", {"title": TEST_MOVIE_TITLE}),
		screen=TEST_SCREEN,
		show_date=today(),
		start_time="09:00:00",
	)
	show.update(kwargs)
	return show


def make_booking(show):
	booking = frappe.get_doc(
		doctype="Ticket Booking",
		show=show,
		customer_name="Test Customer",
		customer_email="customer@example.com",
		customer_phone="9999999999",
	)
	booking.append("seats", {"seat_label": "A-1", "row_letter": "A", "seat_number": 1})
	return booking


def cleanup_test_records():
	for booking in frappe.get_all("Ticket Booking", filters={"screen": TEST_SCREEN}, pluck="name"):
		doc = frappe.get_doc("Ticket Booking", booking)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Ticket Booking", booking, force=True)

	frappe.db.delete("Show", {"screen": TEST_SCREEN})
	frappe.db.delete("Screen", {"name": TEST_SCREEN})
	frappe.db.delete("Theater", {"name": TEST_THEATER})
	frappe.db.delete("Movie", {"title": TEST_ENDED_MOVIE_TITLE})
	frappe.db.delete("Movie", {"title": TEST_MOVIE_TITLE})
	frappe.db.delete("Movie Genre", {"name": TEST_GENRE})