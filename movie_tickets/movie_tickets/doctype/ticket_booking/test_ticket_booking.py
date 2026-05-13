import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_time, today


TEST_GENRE = "Booking Test Genre"
TEST_MOVIE_TITLE = "Booking Test Movie"
TEST_THEATER = "Booking Test Theater - Ahmedabad"
TEST_SCREEN = f"{TEST_THEATER}-Screen 1"
TEST_SCREEN_100 = f"{TEST_THEATER}-Screen 100"


class TestTicketBooking(IntegrationTestCase):
	def setUp(self):
		set_booking_configuration_defaults()
		cleanup_test_records()
		create_test_records()

	def tearDown(self):
		cleanup_test_records()
		set_booking_configuration_defaults()

	def test_booking_details_are_fetched_from_show(self):
		booking = make_booking().insert()

		self.assertEqual(booking.movie_title, TEST_MOVIE_TITLE)
		self.assertEqual(booking.theater, TEST_THEATER)
		self.assertEqual(booking.screen, TEST_SCREEN)
		self.assertEqual(str(booking.show_date), today())
		self.assertEqual(get_time(booking.start_time), get_time("09:00:00"))
		self.assertEqual(booking.price_per_seat, 250)

	def test_booking_totals_are_calculated_from_seats(self):
		booking = make_booking().insert()

		self.assertEqual(booking.number_of_seats, 2)
		self.assertEqual(booking.seats[0].seat_price, 250)
		self.assertEqual(booking.seats[1].seat_price, 300)
		self.assertEqual(booking.total_amount, 550)

	def test_zero_seat_price_defaults_from_show_ticket_price(self):
		booking = make_booking()
		booking.seats[0].seat_price = 0
		booking.insert()

		self.assertEqual(booking.seats[0].seat_price, 250)

	def test_booking_defaults_and_submit(self):
		booking = make_booking().insert()

		self.assertEqual(booking.payment_status, "Unpaid")
		self.assertEqual(booking.booking_status, "Pending")
		self.assertEqual(booking.booked_by, frappe.session.user)
		self.assertTrue(booking.booking_time)

		booking.submit()
		self.assertEqual(booking.docstatus, 1)
		self.assertEqual(booking.booking_status, "Confirmed")
		self.assertEqual(booking.payment_status, "Paid")
		self.assertEqual(frappe.db.get_value("Show", booking.show, "booked_seats"), 2)
		self.assertEqual(frappe.db.get_value("Show", booking.show, "available_seats"), 148)

	def test_cancellation_updates_status_refund_and_show_seats(self):
		future_show = make_show(show_date=add_days(today(), 2)).insert()
		booking = make_booking(show=future_show.name).insert()
		booking.submit()
		booking.cancel()

		booking.reload()
		self.assertEqual(booking.booking_status, "Cancelled")
		self.assertEqual(booking.payment_status, "Refunded")
		self.assertEqual(booking.refund_amount, booking.total_amount)
		self.assertTrue(booking.cancellation_time)
		self.assertEqual(frappe.db.get_value("Show", future_show.name, "booked_seats"), 0)
		self.assertEqual(frappe.db.get_value("Show", future_show.name, "available_seats"), 150)

	def test_cancellation_uses_configured_partial_refund_percentage(self):
		frappe.db.set_single_value("Booking Configuration", "full_refund_hours", 1000)
		frappe.db.set_single_value("Booking Configuration", "partial_refund_hours", 0)
		frappe.db.set_single_value("Booking Configuration", "partial_refund_pct", 25)
		future_show = make_show(show_date=add_days(today(), 2)).insert()
		booking = make_booking(show=future_show.name).insert()
		booking.submit()

		booking.cancel()

		booking.reload()
		self.assertEqual(booking.refund_amount, booking.total_amount * 0.25)

	def test_cannot_book_cancelled_show(self):
		show = frappe.get_doc("Show", frappe.db.get_value("Show", {"screen": TEST_SCREEN}))
		show.show_status = "Cancelled"
		show.save()

		booking = make_booking()

		self.assertRaises(frappe.ValidationError, booking.insert)

	def test_duplicate_seats_within_same_booking_are_invalid(self):
		booking = make_booking()
		booking.seats[1].seat_label = "A-1"
		booking.seats[1].seat_number = 1

		self.assertRaises(frappe.ValidationError, booking.insert)

	def test_seat_must_be_available_for_show(self):
		make_booking().insert()
		booking = make_booking()

		self.assertRaises(frappe.ValidationError, booking.insert)

	def test_max_ten_seats_per_booking(self):
		booking = make_booking(seats=[])
		for seat_number in range(1, 12):
			booking.append(
				"seats",
				{"seat_label": f"A-{seat_number}", "row_letter": "A", "seat_number": seat_number},
			)

		self.assertRaises(frappe.ValidationError, booking.insert)

	def test_max_seats_per_booking_uses_configuration(self):
		frappe.db.set_single_value("Booking Configuration", "max_seats_per_booking", 1)
		booking = make_booking()

		self.assertRaises(frappe.ValidationError, booking.insert)

	def test_seat_label_must_be_within_screen_layout(self):
		booking = make_booking(seats=[])
		booking.append("seats", {"seat_label": "K-1", "row_letter": "K", "seat_number": 1})

		self.assertRaises(frappe.ValidationError, booking.insert)

	# ── Task 3.5: Requested Tests ────────────────────────────────────────────

	def test_booking_decreases_available_seats(self):
		"""Create a show with 100 seats. Book 3 seats. Assert available_seats=97, booked_seats=3."""
		screen = frappe.get_doc(
			doctype="Screen",
			screen_name="Screen 100",
			theater=TEST_THEATER,
			total_seats=100,
			seat_rows=10,
			seats_per_row=10,
			base_price=200,
		).insert()

		show = frappe.get_doc(
			doctype="Show",
			movie=frappe.db.get_value("Movie", {"title": TEST_MOVIE_TITLE}),
			screen=screen.name,
			show_date=today(),
			start_time="18:00:00",
		).insert()

		booking = frappe.get_doc(
			doctype="Ticket Booking",
			show=show.name,
			customer_name="Test Customer",
			customer_email="customer@example.com",
			customer_phone="9999999999",
		)
		booking.append("seats", {"seat_label": "A-1", "row_letter": "A", "seat_number": 1})
		booking.append("seats", {"seat_label": "A-2", "row_letter": "A", "seat_number": 2})
		booking.append("seats", {"seat_label": "A-3", "row_letter": "A", "seat_number": 3})
		booking.insert()
		booking.submit()

		show.reload()
		self.assertEqual(show.booked_seats, 3)
		self.assertEqual(show.available_seats, 97)

	def test_cannot_book_already_taken_seat(self):
		"""Book seat A-1. Attempt another booking with A-1 for same show. Assert ValidationError."""
		booking1 = make_booking(seats=[])
		booking1.append("seats", {"seat_label": "A-1", "row_letter": "A", "seat_number": 1})
		booking1.insert()

		booking2 = make_booking(seats=[])
		booking2.append("seats", {"seat_label": "A-1", "row_letter": "A", "seat_number": 1})

		self.assertRaises(frappe.ValidationError, booking2.insert)

	def test_cannot_book_for_cancelled_show(self):
		"""Cancel a show. Attempt booking. Assert error about show status."""
		show = frappe.get_doc("Show", frappe.db.get_value("Show", {"screen": TEST_SCREEN}))
		show.show_status = "Cancelled"
		show.save()

		booking = make_booking()
		self.assertRaises(frappe.ValidationError, booking.insert)

	def test_max_seats_per_booking_limit(self):
		"""Book 11 seats in one booking (exceeds max 10). Assert validation error."""
		booking = make_booking(seats=[])
		for seat_number in range(1, 12):
			booking.append(
				"seats",
				{"seat_label": f"A-{seat_number}", "row_letter": "A", "seat_number": seat_number},
			)

		self.assertRaises(frappe.ValidationError, booking.insert)

	def test_full_refund_on_early_cancellation(self):
		"""Book for a show far away. Cancel. Assert refund_amount = total_amount."""
		# Default full_refund_hours=4; show is 48+ hours away → full refund
		future_show = make_show(show_date=add_days(today(), 2)).insert()
		booking = make_booking(show=future_show.name).insert()
		booking.submit()
		booking.cancel()

		booking.reload()
		self.assertEqual(booking.refund_amount, booking.total_amount)
		self.assertEqual(booking.payment_status, "Refunded")

	def test_partial_refund_on_late_cancellation(self):
		"""Cancel when hours_until_show is between partial and full thresholds. Assert 50% refund."""
		# Set full_refund_hours very high so it fails, partial threshold to 0
		frappe.db.set_single_value("Booking Configuration", "full_refund_hours", 9999)
		frappe.db.set_single_value("Booking Configuration", "partial_refund_hours", 0)
		frappe.db.set_single_value("Booking Configuration", "partial_refund_pct", 50)

		future_show = make_show(show_date=add_days(today(), 2)).insert()
		booking = make_booking(show=future_show.name).insert()
		booking.submit()
		booking.cancel()

		booking.reload()
		self.assertEqual(booking.refund_amount, booking.total_amount * 0.50)
		self.assertEqual(booking.payment_status, "Refunded")

	def test_no_refund_on_very_late_cancellation(self):
		"""Cancel when hours_until_show is below partial threshold. Assert refund_amount = 0."""
		# Set both thresholds impossibly high so cancellation gets zero refund
		frappe.db.set_single_value("Booking Configuration", "full_refund_hours", 9999)
		frappe.db.set_single_value("Booking Configuration", "partial_refund_hours", 9999)

		future_show = make_show(show_date=add_days(today(), 2)).insert()
		booking = make_booking(show=future_show.name).insert()
		booking.submit()
		booking.cancel()

		booking.reload()
		self.assertEqual(booking.refund_amount, 0)

	def test_show_conflict_validation(self):
		"""Create show at 14:00-16:00. Overlapping show at 15:00 on same screen/date. Assert error."""
		# Existing movie is 120 min, so 14:00 → 16:00
		make_show(start_time="14:00:00").insert()
		conflicting_show = make_show(start_time="15:00:00")

		self.assertRaises(frappe.ValidationError, conflicting_show.insert)

	def test_cancel_restores_seats(self):
		"""Book 4 seats, submit, then cancel. Assert available_seats restored."""
		future_show = make_show(show_date=add_days(today(), 2)).insert()

		original_available = frappe.db.get_value("Show", future_show.name, "available_seats")

		booking = make_booking(show=future_show.name, seats=[])
		for i in range(1, 5):
			booking.append("seats", {"seat_label": f"A-{i}", "row_letter": "A", "seat_number": i})
		booking.insert()
		booking.submit()

		self.assertEqual(frappe.db.get_value("Show", future_show.name, "available_seats"), original_available - 4)
		self.assertEqual(frappe.db.get_value("Show", future_show.name, "booked_seats"), 4)

		booking.cancel()

		self.assertEqual(frappe.db.get_value("Show", future_show.name, "available_seats"), original_available)
		self.assertEqual(frappe.db.get_value("Show", future_show.name, "booked_seats"), 0)


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
		theater_name="Booking Test Theater",
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

	frappe.get_doc(
		doctype="Show",
		movie=movie.name,
		screen=TEST_SCREEN,
		show_date=today(),
		start_time="09:00:00",
	).insert()


def make_show(**kwargs):
	show = frappe.get_doc(
		doctype="Show",
		movie=frappe.db.get_value("Movie", {"title": TEST_MOVIE_TITLE}),
		screen=TEST_SCREEN,
		show_date=today(),
		start_time="13:00:00",
	)
	show.update(kwargs)
	return show


def make_booking(**kwargs):
	booking = frappe.get_doc(
		doctype="Ticket Booking",
		show=frappe.db.get_value("Show", {"screen": TEST_SCREEN}),
		customer_name="Test Customer",
		customer_email="customer@example.com",
		customer_phone="9999999999",
	)
	booking.append("seats", {"seat_label": "A-1", "row_letter": "A", "seat_number": 1})
	booking.append("seats", {"seat_label": "A-2", "row_letter": "A", "seat_number": 2, "seat_price": 300})
	booking.update(kwargs)
	return booking


def set_booking_configuration_defaults():
	frappe.db.set_single_value("Booking Configuration", "max_seats_per_booking", 10)
	frappe.db.set_single_value("Booking Configuration", "booking_expiry_minutes", 15)
	frappe.db.set_single_value("Booking Configuration", "full_refund_hours", 4)
	frappe.db.set_single_value("Booking Configuration", "partial_refund_hours", 2)
	frappe.db.set_single_value("Booking Configuration", "partial_refund_pct", 50)
	frappe.db.set_single_value("Booking Configuration", "full_refund_hours", 4)
	frappe.db.set_single_value("Booking Configuration", "partial_refund_hours", 2)
	frappe.db.set_single_value("Booking Configuration", "partial_refund_pct", 50)
	frappe.db.set_single_value("Booking Configuration", "enable_auto_expiry", 1)
	frappe.db.set_single_value("Booking Configuration", "booking_open_days_before", 7)


def cleanup_test_records():
	for screen in (TEST_SCREEN, TEST_SCREEN_100):
		for booking in frappe.get_all("Ticket Booking", filters={"screen": screen}, pluck="name"):
			doc = frappe.get_doc("Ticket Booking", booking)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Ticket Booking", booking, force=True)

		frappe.db.delete("Show", {"screen": screen})
		frappe.db.delete("Screen", {"name": screen})

	frappe.db.delete("Theater", {"name": TEST_THEATER})
	frappe.db.delete("Movie", {"title": TEST_MOVIE_TITLE})
	frappe.db.delete("Movie Genre", {"name": TEST_GENRE})