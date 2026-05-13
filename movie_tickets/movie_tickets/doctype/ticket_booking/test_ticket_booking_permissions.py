import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking import (
	get_permission_query_conditions,
	get_max_seats_per_booking,
)


TEST_GENRE = "Permission Test Genre"
TEST_MOVIE_TITLE = "Permission Test Movie"
TEST_THEATER = "Permission Test Theater - Ahmedabad"
TEST_SCREEN = f"{TEST_THEATER}-Screen 1"
MANAGER_USER = "manager@test.com"
STAFF_USER = "staff@test.com"
CUSTOMER_USER = "customer@test.com"
OTHER_CUSTOMER_USER = "other.customer@test.com"


class TestTicketBookingPermissions(IntegrationTestCase):
	def setUp(self):
		cleanup_test_records()
		create_roles_and_users()
		reload_movie_ticket_doctypes()
		create_test_records()

	def tearDown(self):
		frappe.set_user("Administrator")
		cleanup_test_records()

	def test_customer_can_only_access_own_booking(self):
		own_booking = make_booking(CUSTOMER_USER, "A-1", 1).insert()
		other_booking = make_booking(OTHER_CUSTOMER_USER, "A-2", 2).insert()

		frappe.set_user(CUSTOMER_USER)
		visible_bookings = frappe.get_list("Ticket Booking", pluck="name", order_by="name asc")

		self.assertIn(own_booking.name, visible_bookings)
		self.assertNotIn(other_booking.name, visible_bookings)
		self.assertTrue(own_booking.has_permission("read", user=CUSTOMER_USER))
		self.assertFalse(other_booking.has_permission("read", user=CUSTOMER_USER))
		self.assertIn(CUSTOMER_USER, get_permission_query_conditions(CUSTOMER_USER))

	def test_manager_and_staff_can_access_all_bookings(self):
		first_booking = make_booking(CUSTOMER_USER, "A-1", 1).insert()
		second_booking = make_booking(OTHER_CUSTOMER_USER, "A-2", 2).insert()

		for user in (MANAGER_USER, STAFF_USER):
			frappe.set_user(user)
			visible_bookings = frappe.get_list("Ticket Booking", pluck="name", order_by="name asc")

			self.assertIn(first_booking.name, visible_bookings)
			self.assertIn(second_booking.name, visible_bookings)
			self.assertTrue(first_booking.has_permission("read", user=user))
			self.assertTrue(second_booking.has_permission("read", user=user))

	def test_booking_configuration_is_manager_only(self):
		self.assertTrue(frappe.has_permission("Booking Configuration", "read", user=MANAGER_USER))
		self.assertFalse(frappe.has_permission("Booking Configuration", "read", user=STAFF_USER))
		self.assertFalse(frappe.has_permission("Booking Configuration", "read", user=CUSTOMER_USER))

	def test_default_all_role_can_select_show_and_open_seat_picker_dependencies(self):
		frappe.set_user(CUSTOMER_USER)

		self.assertTrue(frappe.has_permission("Show", "select", user=CUSTOMER_USER))
		self.assertTrue(frappe.has_permission("Movie", "select", user=CUSTOMER_USER))
		self.assertTrue(frappe.has_permission("Theater", "select", user=CUSTOMER_USER))
		self.assertTrue(frappe.has_permission("Screen", "read", user=CUSTOMER_USER))
		self.assertEqual(get_max_seats_per_booking(), 10)

		shows = frappe.get_list("Show", filters={"screen": TEST_SCREEN}, fields=["name", "screen"], limit=1)
		self.assertTrue(shows)
		self.assertEqual(shows[0].screen, TEST_SCREEN)


def create_roles_and_users():
	for role in ("Cinema Manager", "Box Office Staff", "Customer"):
		if not frappe.db.exists("Role", role):
			frappe.get_doc(doctype="Role", role_name=role, desk_access=1).insert(ignore_permissions=True)

	create_user(MANAGER_USER, "Cinema", "Manager", "Cinema Manager")
	create_user(STAFF_USER, "Box Office", "Staff", "Box Office Staff")
	create_user(CUSTOMER_USER, "Test", "Customer", "Customer")
	create_user(OTHER_CUSTOMER_USER, "Other", "Customer", "Customer")


def create_user(email, first_name, last_name, role):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		user.enabled = 1
		user.set("roles", [])
		user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
		return

	user = frappe.get_doc(
		doctype="User",
		email=email,
		first_name=first_name,
		last_name=last_name,
		enabled=1,
		send_welcome_email=0,
		new_password="test",
		user_type="System User",
	)
	user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)


def reload_movie_ticket_doctypes():
	for doctype in (
		"movie_genre",
		"movie",
		"theater",
		"screen",
		"show",
		"ticket_booking",
		"booking_configuration",
	):
		frappe.reload_doc("movie_tickets", "doctype", doctype)


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
		theater_name="Permission Test Theater",
		city="Ahmedabad",
		address="CG Road, Ahmedabad",
	).insert()

	frappe.get_doc(
		doctype="Screen",
		screen_name="Screen 1",
		theater=TEST_THEATER,
		total_seats=20,
		seat_rows=2,
		seats_per_row=10,
		base_price=250,
	).insert()

	frappe.get_doc(
		doctype="Show",
		movie=movie.name,
		screen=TEST_SCREEN,
		show_date=today(),
		start_time="09:00:00",
	).insert()


def make_booking(booked_by, seat_label, seat_number):
	booking = frappe.get_doc(
		doctype="Ticket Booking",
		show=frappe.db.get_value("Show", {"screen": TEST_SCREEN}),
		customer_name="Permission Customer",
		customer_email=booked_by,
		customer_phone="9999999999",
		booked_by=booked_by,
	)
	booking.append(
		"seats",
		{"seat_label": seat_label, "row_letter": seat_label.split("-")[0], "seat_number": seat_number},
	)
	return booking


def cleanup_test_records():
	frappe.set_user("Administrator")

	for booking in frappe.get_all("Ticket Booking", filters={"screen": TEST_SCREEN}, pluck="name"):
		doc = frappe.get_doc("Ticket Booking", booking)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc("Ticket Booking", booking, force=True)

	frappe.db.delete("Show", {"screen": TEST_SCREEN})
	frappe.db.delete("Screen", {"name": TEST_SCREEN})
	frappe.db.delete("Theater", {"name": TEST_THEATER})
	frappe.db.delete("Movie", {"title": TEST_MOVIE_TITLE})
	frappe.db.delete("Movie Genre", {"name": TEST_GENRE})
