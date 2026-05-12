import frappe
from frappe.tests import IntegrationTestCase


TEST_GENRE = "TestGenreDuplicate"


class TestMovieGenre(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Movie Genre", {"genre_name": ["in", [TEST_GENRE, TEST_GENRE.lower()]]})

	def test_duplicate_genre_name_is_case_insensitive(self):
		frappe.get_doc(doctype="Movie Genre", genre_name=TEST_GENRE).insert()

		duplicate = frappe.get_doc(doctype="Movie Genre", genre_name=TEST_GENRE.lower())

		self.assertRaises(frappe.DuplicateEntryError, duplicate.insert)