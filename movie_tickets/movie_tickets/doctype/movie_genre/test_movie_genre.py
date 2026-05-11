import frappe
from frappe.tests import IntegrationTestCase


class TestMovieGenre(IntegrationTestCase):
	def tearDown(self):
		frappe.db.delete("Movie Genre", {"genre_name": ["in", ["Action", "action"]]})

	def test_duplicate_genre_name_is_case_insensitive(self):
		frappe.get_doc(doctype="Movie Genre", genre_name="Action").insert()

		duplicate = frappe.get_doc(doctype="Movie Genre", genre_name="action")

		self.assertRaises(frappe.DuplicateEntryError, duplicate.insert)