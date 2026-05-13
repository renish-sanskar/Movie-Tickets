import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today


TEST_GENRE = "Movie Test Genre"


class TestMovie(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Movie Genre", TEST_GENRE):
			frappe.get_doc(doctype="Movie Genre", genre_name=TEST_GENRE).insert()

	def tearDown(self):
		frappe.db.delete("Movie", {"genre": TEST_GENRE})
		frappe.db.delete("Movie Genre", {"name": TEST_GENRE})

	def test_slug_is_generated_from_title(self):
		movie = make_movie(title="The Dark Knight")
		movie.insert()

		self.assertEqual(movie.slug, "the-dark-knight")

	def test_movie_status_is_computed_from_dates(self):
		upcoming_movie = make_movie(title="Future Movie", release_date=add_days(today(), 1))
		upcoming_movie.insert()
		self.assertEqual(upcoming_movie.movie_status, "Upcoming")

		now_showing_movie = make_movie(
			title="Current Movie",
			release_date=add_days(today(), -1),
			end_date=add_days(today(), 1),
		)
		now_showing_movie.insert()
		self.assertEqual(now_showing_movie.movie_status, "Now Showing")

		ended_movie = make_movie(
			title="Past Movie",
			release_date=add_days(today(), -3),
			end_date=add_days(today(), -1),
		)
		ended_movie.insert()
		self.assertEqual(ended_movie.movie_status, "Ended")

	def test_end_date_must_be_after_release_date(self):
		movie = make_movie(end_date=today())

		self.assertRaises(frappe.ValidationError, movie.insert)

	def test_duration_minutes_must_be_between_one_and_six_hundred(self):
		short_movie = make_movie(title="Short Movie", duration_minutes=0)
		long_movie = make_movie(title="Long Movie", duration_minutes=601)

		self.assertRaises(frappe.ValidationError, short_movie.insert)
		self.assertRaises(frappe.ValidationError, long_movie.insert)


def make_movie(**kwargs):
	movie = frappe.get_doc(
		doctype="Movie",
		title="Test Movie",
		language="English",
		genre=TEST_GENRE,
		duration_minutes=120,
		release_date=today(),
	)
	movie.update(kwargs)
	return movie