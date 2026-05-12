import frappe
from frappe.utils import today, add_days, formatdate


CINEMA_MANAGER_ROLES = ("System Manager", "Cinema Manager", "Box Office Staff")


def _check_access():
	roles = frappe.get_roles()
	if not any(r in roles for r in CINEMA_MANAGER_ROLES):
		frappe.throw("Not permitted", frappe.PermissionError)


@frappe.whitelist()
def get_occupancy_by_theater():
	"""Today's occupancy per theater: booked_seats / total_seats."""
	_check_access()
	data = frappe.db.sql(
		"""
		SELECT s.theater AS theater,
		       SUM(s.booked_seats) AS booked,
		       SUM(s.total_seats) AS total
		FROM `tabShow` s
		WHERE s.show_date = %s
		  AND s.show_status != 'Cancelled'
		GROUP BY s.theater
		ORDER BY s.theater
		""",
		(today(),),
		as_dict=True,
	)
	return {
		"labels": [d.theater for d in data],
		"booked": [d.booked or 0 for d in data],
		"total": [d.total or 0 for d in data],
	}


@frappe.whitelist()
def get_revenue_trend():
	"""Daily confirmed-booking revenue for the last 30 days."""
	_check_access()
	start = add_days(today(), -29)
	data = frappe.db.sql(
		"""
		SELECT tb.show_date AS date, SUM(tb.total_amount) AS revenue
		FROM `tabTicket Booking` tb
		WHERE tb.docstatus = 1
		  AND tb.booking_status = 'Confirmed'
		  AND tb.show_date BETWEEN %s AND %s
		GROUP BY tb.show_date
		ORDER BY tb.show_date
		""",
		(start, today()),
		as_dict=True,
	)
	# fill gaps so every day appears
	date_map = {str(d.date): float(d.revenue or 0) for d in data}
	labels, values = [], []
	prev_month = None
	for i in range(30):
		dt = add_days(today(), -29 + i)
		from frappe.utils import getdate
		d = getdate(dt)
		if d.month != prev_month:
			labels.append(f"{d.day} {d.strftime('%b')}")
			prev_month = d.month
		else:
			labels.append(str(d.day))
		values.append(date_map.get(str(dt), 0))
	return {"labels": labels, "values": values}


@frappe.whitelist()
def get_bookings_by_time_slot():
	"""Bookings grouped into 2-hour time slots."""
	_check_access()
	data = frappe.db.sql(
		"""
		SELECT
			CASE
				WHEN HOUR(tb.start_time) < 10 THEN 'Before 10 AM'
				WHEN HOUR(tb.start_time) < 12 THEN '10 AM - 12 PM'
				WHEN HOUR(tb.start_time) < 14 THEN '12 - 2 PM'
				WHEN HOUR(tb.start_time) < 16 THEN '2 - 4 PM'
				WHEN HOUR(tb.start_time) < 18 THEN '4 - 6 PM'
				WHEN HOUR(tb.start_time) < 20 THEN '6 - 8 PM'
				WHEN HOUR(tb.start_time) < 22 THEN '8 - 10 PM'
				ELSE '10 PM+'
			END AS slot,
			CASE
				WHEN HOUR(tb.start_time) < 10 THEN 1
				WHEN HOUR(tb.start_time) < 12 THEN 2
				WHEN HOUR(tb.start_time) < 14 THEN 3
				WHEN HOUR(tb.start_time) < 16 THEN 4
				WHEN HOUR(tb.start_time) < 18 THEN 5
				WHEN HOUR(tb.start_time) < 20 THEN 6
				WHEN HOUR(tb.start_time) < 22 THEN 7
				ELSE 8
			END AS slot_order,
			COUNT(*) AS count
		FROM `tabTicket Booking` tb
		WHERE tb.docstatus = 1
		  AND tb.booking_status = 'Confirmed'
		GROUP BY slot, slot_order
		ORDER BY slot_order
		""",
		as_dict=True,
	)
	return {
		"labels": [d.slot for d in data],
		"values": [d.count for d in data],
	}


@frappe.whitelist()
def get_top_movies():
	"""Top 5 movies by confirmed bookings (all time)."""
	_check_access()
	data = frappe.db.sql(
		"""
		SELECT tb.movie_title AS movie, COUNT(*) AS count
		FROM `tabTicket Booking` tb
		WHERE tb.docstatus = 1
		  AND tb.booking_status = 'Confirmed'
		GROUP BY tb.movie_title
		ORDER BY count DESC
		LIMIT 5
		""",
		as_dict=True,
	)
	return {
		"labels": [d.movie for d in data],
		"values": [d.count for d in data],
	}
