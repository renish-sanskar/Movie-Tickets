import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from movie_tickets.api import (
	create_booking,
	get_seat_availability,
	get_shows_for_movie,
	send_booking_confirmation,
)


TEST_GENRE = "API Test Genre"
TEST_MOVIE_TITLE = "API Test Movie"
TEST_THEATER = "API Test Theater - Ahmedabad"
TEST_SCREEN = f"{TEST_THEATER}-Screen 1"
TEST_SURAT_THEATER = "API Test Theater - Surat"
TEST_SURAT_SCREEN = f"{TEST_SURAT_THEATER}-Screen 1"


class TestMovieTicketsAPI(IntegrationTestCase):
	def setUp(self):
		set_booking_configuration_defaults()
		cleanup_test_records()
		create_test_records()

	def tearDown(self):
		cleanup_test_records()
		set_booking_configuration_defaults()

	def test_get_seat_availability_returns_layout_and_booking_statuses(self):
		show = get_primary_show()
		make_booking(seat_label="A-1", seat_number=1).insert()
		confirmed_booking = make_booking(seat_label="B-2", row_letter="B", seat_number=2).insert()
		confirmed_booking.submit()

		availability = get_seat_availability(show)

		self.assertEqual(availability["total_rows"], 2)
		self.assertEqual(availability["seats_per_row"], 3)
		self.assertEqual(len(availability["seats"]), 2)
		self.assertEqual(len(availability["seats"][0]), 3)
		self.assertEqual(availability["seats"][0][0], {"seat_label": "A-1", "status": "booked"})
		self.assertEqual(availability["seats"][0][1], {"seat_label": "A-2", "status": "available"})
		self.assertEqual(availability["seats"][1][1], {"seat_label": "B-2", "status": "booked"})

	def test_create_booking_returns_booking_details(self):
		show = get_primary_show()

		response = create_booking(
			show,
			"API Customer",
			"api.customer@example.com",
			"9999999999",
			["A-1", {"seat_label": "A-2"}],
		)

		booking = frappe.get_doc("Ticket Booking", response["booking_name"])
		self.assertTrue(response["success"])
		self.assertEqual(booking.show, show)
		self.assertEqual(booking.customer_name, "API Customer")
		self.assertEqual(booking.number_of_seats, 2)
		self.assertEqual(response["total_amount"], 500)
		self.assertEqual(response["total_amount"], booking.total_amount)
		self.assertEqual(response["message"], "Booking created. Complete payment within 15 minutes.")

	def test_create_booking_revalidates_seat_availability(self):
		show = get_primary_show()
		make_booking(seat_label="A-1", seat_number=1).insert()

		self.assertRaises(
			frappe.ValidationError,
			create_booking,
			show,
			"API Customer",
			"api.customer@example.com",
			"9999999999",
			["A-1"],
		)

	def test_get_shows_for_movie_returns_upcoming_shows(self):
		movie = frappe.db.get_value("Movie", {"title": TEST_MOVIE_TITLE})

		shows = get_shows_for_movie(movie)

		self.assertEqual(len(shows), 2)
		self.assertEqual(shows[0].theater, TEST_THEATER)
		self.assertEqual(shows[0].screen, TEST_SCREEN)
		self.assertEqual(shows[0].screen_type, "IMAX")
		self.assertEqual(str(shows[0].show_date), add_days(today(), 1))
		self.assertEqual(str(shows[0].start_time), "9:00:00")
		self.assertEqual(shows[0].ticket_price, 250)
		self.assertEqual(shows[0].available_seats, 6)
		self.assertEqual(shows[1].theater, TEST_SURAT_THEATER)

	def test_get_shows_for_movie_filters_by_city_and_date(self):
		movie = frappe.db.get_value("Movie", {"title": TEST_MOVIE_TITLE})

		city_shows = get_shows_for_movie(movie, city="Surat")
		date_shows = get_shows_for_movie(movie, date=add_days(today(), 2))

		self.assertEqual(len(city_shows), 1)
		self.assertEqual(city_shows[0].theater, TEST_SURAT_THEATER)
		self.assertEqual(len(date_shows), 1)
		self.assertEqual(str(date_shows[0].show_date), add_days(today(), 2))

	def test_send_booking_confirmation_sends_formatted_email(self):
		booking = make_booking(seat_label="A-1", seat_number=1).insert()
		sent_messages = []
		original_sendmail = frappe.sendmail

		def capture_sendmail(**kwargs):
			sent_messages.append(kwargs)

		frappe.sendmail = capture_sendmail
		try:
			response = send_booking_confirmation(booking.name)
		finally:
			frappe.sendmail = original_sendmail

		self.assertTrue(response["success"])
		self.assertEqual(response["booking_name"], booking.name)
		self.assertEqual(len(sent_messages), 1)
		self.assertEqual(sent_messages[0]["recipients"], [booking.customer_email])
		self.assertIn(booking.name, sent_messages[0]["subject"])

		email_html = sent_messages[0]["message"]
		self.assertIn(booking.name, email_html)
		self.assertIn(TEST_MOVIE_TITLE, email_html)
		self.assertIn(TEST_THEATER, email_html)
		self.assertIn(TEST_SCREEN, email_html)
		self.assertIn("9:00:00", email_html)
		self.assertIn("A-1", email_html)
		self.assertIn("250", email_html)


def create_test_records():
	frappe.get_doc(doctype="Movie Genre", genre_name=TEST_GENRE).insert()

	movie = frappe.get_doc(
		doctype="Movie",
		title=TEST_MOVIE_TITLE,
		language="English",
		genre=TEST_GENRE,
		duration_minutes=120,
		release_date=today(),
	).insert()

	frappe.get_doc(
		doctype="Theater",
		theater_name="API Test Theater",
		city="Ahmedabad",
		address="SG Highway, Ahmedabad",
	).insert()

	frappe.get_doc(
		doctype="Screen",
		screen_name="Screen 1",
		theater=TEST_THEATER,
		total_seats=6,
		seat_rows=2,
		seats_per_row=3,
		base_price=250,
		screen_type="IMAX",
	).insert()

	frappe.get_doc(
		doctype="Theater",
		theater_name="API Test Theater",
		city="Surat",
		address="Ring Road, Surat",
	).insert()

	frappe.get_doc(
		doctype="Screen",
		screen_name="Screen 1",
		theater=TEST_SURAT_THEATER,
		total_seats=6,
		seat_rows=2,
		seats_per_row=3,
		base_price=300,
		screen_type="3D",
	).insert()

	frappe.get_doc(
		doctype="Show",
		movie=movie.name,
		screen=TEST_SCREEN,
		show_date=add_days(today(), 1),
		start_time="09:00:00",
	).insert()

	frappe.get_doc(
		doctype="Show",
		movie=movie.name,
		screen=TEST_SURAT_SCREEN,
		show_date=add_days(today(), 2),
		start_time="11:00:00",
	).insert()

	frappe.get_doc(
		doctype="Show",
		movie=movie.name,
		screen=TEST_SCREEN,
		show_date=add_days(today(), 3),
		start_time="13:00:00",
		show_status="Cancelled",
	).insert()


def make_booking(seat_label, seat_number, row_letter="A"):
	booking = frappe.get_doc(
		doctype="Ticket Booking",
		show=get_primary_show(),
		customer_name="API Test Customer",
		customer_email="api.customer@example.com",
		customer_phone="9999999999",
	)
	booking.append(
		"seats",
		{"seat_label": seat_label, "row_letter": row_letter, "seat_number": seat_number},
	)
	return booking


def get_primary_show():
	return frappe.db.get_value(
		"Show",
		{"screen": TEST_SCREEN, "show_status": "Scheduled"},
		order_by="show_date asc, start_time asc",
	)


def cleanup_test_records():
	for booking in frappe.get_all("Ticket Booking", filters={"screen": ["in", [TEST_SCREEN, TEST_SURAT_SCREEN]]}, pluck="name"):
		doc = frappe.get_doc("Ticket Booking", booking)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Ticket Booking", booking, force=True)

	frappe.db.delete("Show", {"screen": ["in", [TEST_SCREEN, TEST_SURAT_SCREEN]]})
	frappe.db.delete("Screen", {"name": TEST_SCREEN})
	frappe.db.delete("Screen", {"name": TEST_SURAT_SCREEN})
	frappe.db.delete("Theater", {"name": TEST_THEATER})
	frappe.db.delete("Theater", {"name": TEST_SURAT_THEATER})
	frappe.db.delete("Movie", {"title": TEST_MOVIE_TITLE})
	frappe.db.delete("Movie Genre", {"name": TEST_GENRE})


def set_booking_configuration_defaults():
	frappe.db.set_single_value("Booking Configuration", "max_seats_per_booking", 10)
	frappe.db.set_single_value("Booking Configuration", "booking_expiry_minutes", 15)
	frappe.db.set_single_value("Booking Configuration", "full_refund_hours", 4)
	frappe.db.set_single_value("Booking Configuration", "partial_refund_hours", 2)
	frappe.db.set_single_value("Booking Configuration", "partial_refund_pct", 50)
	frappe.db.set_single_value("Booking Configuration", "enable_auto_expiry", 1)
	frappe.db.set_single_value("Booking Configuration", "booking_open_days_before", 7)
