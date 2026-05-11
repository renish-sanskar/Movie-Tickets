from frappe.model.document import Document

import frappe


class Theater(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText
		city: DF.Data
		is_active: DF.Check
		phone: DF.Data | None
		theater_name: DF.Data
		total_screens: DF.Int
	# end: auto-generated types

	def autoname(self):
		self.name = f"{self.theater_name.strip()} - {self.city.strip()}"

	def validate(self):
		self.set_total_screens()

	def set_total_screens(self):
		if not self.name or not frappe.db.table_exists("Screen") or not frappe.db.field_exists("Screen", "theater"):
			self.total_screens = 0
			return

		self.total_screens = frappe.db.count("Screen", {"theater": self.name})