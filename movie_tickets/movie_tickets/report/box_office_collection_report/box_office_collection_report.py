# Copyright (c) 2026, Renish Ponkiya and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data, filters)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"fieldname": "movie_title",
			"label": _("Movie Title"),
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"fieldname": "genre",
			"label": _("Genre"),
			"fieldtype": "Link",
			"options": "Movie Genre",
			"width": 120,
		},
		{
			"fieldname": "language",
			"label": _("Language"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "total_shows",
			"label": _("Total Shows"),
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"fieldname": "total_bookings",
			"label": _("Total Bookings"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "total_seats_sold",
			"label": _("Total Seats Sold"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "total_revenue",
			"label": _("Total Revenue"),
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"fieldname": "avg_occupancy",
			"label": _("Avg Occupancy (%)"),
			"fieldtype": "Percent",
			"width": 130,
		},
		{
			"fieldname": "avg_ticket_price",
			"label": _("Avg Ticket Price"),
			"fieldtype": "Currency",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)

	data = frappe.db.sql(
		"""
		SELECT
			m.title AS movie_title,
			m.genre AS genre,
			m.language AS language,
			COUNT(DISTINCT s.name) AS total_shows,
			COUNT(DISTINCT tb.name) AS total_bookings,
			IFNULL(SUM(tb.number_of_seats), 0) AS total_seats_sold,
			IFNULL(SUM(tb.total_amount), 0) AS total_revenue,
			CASE
				WHEN SUM(s.total_seats) > 0
				THEN ROUND(SUM(tb.number_of_seats) / SUM(s.total_seats) * 100, 1)
				ELSE 0
			END AS avg_occupancy,
			CASE
				WHEN SUM(tb.number_of_seats) > 0
				THEN ROUND(SUM(tb.total_amount) / SUM(tb.number_of_seats), 2)
				ELSE 0
			END AS avg_ticket_price
		FROM `tabMovie` m
		INNER JOIN `tabShow` s ON s.movie = m.name
		LEFT JOIN `tabTicket Booking` tb
			ON tb.show = s.name AND tb.docstatus = 1
		WHERE s.show_status != 'Cancelled'
			{conditions}
		GROUP BY m.name, m.title, m.genre, m.language
		ORDER BY total_revenue DESC
		""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	return data


def get_conditions(filters):
	conditions = []

	if filters.get("theater"):
		conditions.append("AND s.theater = %(theater)s")

	if filters.get("from_date"):
		conditions.append("AND s.show_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("AND s.show_date <= %(to_date)s")

	if filters.get("genre"):
		conditions.append("AND m.genre = %(genre)s")

	if filters.get("language"):
		conditions.append("AND m.language = %(language)s")

	return "\n".join(conditions)


def get_chart(data, filters):
	chart_type = (filters or {}).get("chart_type", "Top 10 Movies by Revenue")

	if chart_type == "Revenue by Screen Type":
		return get_screen_type_pie_chart(filters)

	return get_revenue_bar_chart(data)


def get_revenue_bar_chart(data):
	"""Bar chart: top 10 movies by revenue."""
	top_10 = data[:10]

	if not top_10:
		return None

	return {
		"data": {
			"labels": [d.movie_title for d in top_10],
			"datasets": [
				{
					"name": _("Revenue"),
					"values": [d.total_revenue for d in top_10],
				}
			],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
		"barOptions": {"spaceRatio": 0.4},
	}


def get_screen_type_pie_chart(filters):
	"""Pie chart: revenue by screen type (Standard/IMAX/3D/4DX)."""
	conditions = get_conditions(filters)

	screen_data = frappe.db.sql(
		"""
		SELECT
			sc.screen_type AS screen_type,
			IFNULL(SUM(tb.total_amount), 0) AS revenue
		FROM `tabTicket Booking` tb
		INNER JOIN `tabShow` s ON tb.show = s.name
		INNER JOIN `tabScreen` sc ON s.screen = sc.name
		INNER JOIN `tabMovie` m ON s.movie = m.name
		WHERE tb.docstatus = 1
			AND s.show_status != 'Cancelled'
			{conditions}
		GROUP BY sc.screen_type
		ORDER BY revenue DESC
		""".format(conditions=conditions),
		filters,
		as_dict=True,
	)

	if not screen_data:
		return None

	return {
		"data": {
			"labels": [d.screen_type for d in screen_data],
			"datasets": [
				{
					"name": _("Revenue"),
					"values": [d.revenue for d in screen_data],
				}
			],
		},
		"type": "pie",
		"colors": ["#5e64ff", "#ff5e7e", "#ffc107", "#28a745"],
	}


def get_report_summary(data):
	"""Summary cards at the bottom of the report."""
	total_revenue = sum(d.total_revenue for d in data)
	total_bookings = sum(d.total_bookings for d in data)
	total_seats = sum(d.total_seats_sold for d in data)

	return [
		{
			"value": total_revenue,
			"label": _("Total Revenue"),
			"datatype": "Currency",
			"indicator": "green",
		},
		{
			"value": total_bookings,
			"label": _("Total Bookings"),
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": total_seats,
			"label": _("Total Seats Sold"),
			"datatype": "Int",
			"indicator": "blue",
		},
	]
