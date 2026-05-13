import frappe
from frappe import _
from frappe.model.document import Document


class MovieGenre(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		genre_name: DF.Data
		is_active: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_unique_genre_name()

	def validate_unique_genre_name(self):
		if not self.genre_name:
			return

		existing_genre = frappe.db.sql(
			"""
			select name
			from `tabMovie Genre`
			where lower(genre_name) = lower(%s)
				and name != %s
			limit 1
			""",
			(self.genre_name, self.name or ""),
		)

		if existing_genre:
			frappe.throw(
				_("Movie Genre {0} already exists").format(frappe.bold(self.genre_name)),
				frappe.DuplicateEntryError,
			)