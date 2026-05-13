from frappe.model.document import Document


class BookedSeat(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		row_letter: DF.Data
		seat_label: DF.Data
		seat_number: DF.Int
		seat_price: DF.Currency
	# end: auto-generated types

	pass