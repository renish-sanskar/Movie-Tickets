import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class Movie(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cast: DF.SmallText | None
		director: DF.Data | None
		duration_minutes: DF.Int
		end_date: DF.Date | None
		genre: DF.Link
		language: DF.Literal["English", "Hindi", "Gujarati", "Tamil", "Telugu", "Other"]
		movie_status: DF.Literal["Upcoming", "Now Showing", "Ended"]
		naming_series: DF.Literal["MOV-.#####"]
		poster: DF.AttachImage | None
		rating: DF.Literal["U", "UA", "A", "S"]
		release_date: DF.Date
		slug: DF.Data | None
		synopsis: DF.TextEditor | None
		title: DF.Data
		trailer_url: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_dates()
		self.validate_duration_minutes()

	def before_save(self):
		self.set_slug()
		self.set_movie_status()

	def set_slug(self):
		self.slug = make_slug(self.title)

	def set_movie_status(self):
		if not self.release_date:
			self.movie_status = "Upcoming"
			return

		current_date = getdate(today())
		release_date = getdate(self.release_date)
		end_date = getdate(self.end_date) if self.end_date else None

		if current_date < release_date:
			self.movie_status = "Upcoming"
		elif end_date and current_date > end_date:
			self.movie_status = "Ended"
		else:
			self.movie_status = "Now Showing"

	def validate_dates(self):
		if self.release_date and self.end_date and getdate(self.end_date) <= getdate(self.release_date):
			frappe.throw(_("End Date must be after Release Date"))

	def validate_duration_minutes(self):
		if self.duration_minutes is None:
			return

		if self.duration_minutes < 1 or self.duration_minutes > 600:
			frappe.throw(_("Duration Minutes must be between 1 and 600"))


def make_slug(title):
	title = title or ""
	slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
	return re.sub(r"-+", "-", slug)