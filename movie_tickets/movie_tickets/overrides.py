import frappe
from frappe.client import get_count as original_get_count


@frappe.whitelist()
def get_count_with_logging(doctype, filters=None, debug=False, cache=False):
	"""
	Wrapper around frappe.client.get_count that logs the DocType and filters
	being queried. Demonstrates override_whitelisted_methods in hooks.py.

	This override intercepts ALL calls to frappe.client.get_count — from
	list views, dashboards, sidebar counts, and custom scripts.
	"""
	frappe.logger("movie_tickets").info(
		f"get_count called | DocType: {doctype} | Filters: {filters} | User: {frappe.session.user}"
	)

	# Call the original Frappe function unchanged
	return original_get_count(doctype, filters=filters, debug=debug, cache=cache)
