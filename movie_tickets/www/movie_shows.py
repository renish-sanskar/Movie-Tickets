import frappe
from collections import OrderedDict


no_cache = 1
allow_guest = True


def get_context(context):
	movie_id = frappe.form_dict.get("movie")
	if not movie_id:
		frappe.throw("Please select a movie", frappe.DoesNotExistError)

	movie = frappe.db.get_value(
		"Movie",
		movie_id,
		["name", "title", "slug", "poster", "language", "genre", "duration_minutes", "rating"],
		as_dict=True,
	)

	if not movie:
		frappe.throw("Movie not found", frappe.DoesNotExistError)

	context.movie = movie
	context.title = f"Shows - {movie.title}"

	shows = frappe.get_all(
		"Show",
		filters={
			"movie": movie_id,
			"show_status": ["in", ["Scheduled", "Now Playing"]],
			"show_date": [">=", frappe.utils.today()],
		},
		fields=[
			"name", "screen", "theater", "show_date", "start_time",
			"ticket_price", "available_seats", "total_seats", "show_status",
		],
		order_by="show_date asc, start_time asc",
	)

	# Fetch theater and screen details
	theaters = {}
	screens = {}
	for show in shows:
		if show.theater and show.theater not in theaters:
			theaters[show.theater] = frappe.db.get_value(
				"Theater", show.theater, ["theater_name", "city", "address"], as_dict=True
			)
		if show.screen and show.screen not in screens:
			screens[show.screen] = frappe.db.get_value(
				"Screen", show.screen, ["screen_name", "screen_type"], as_dict=True
			)

	# Group by theater → date
	grouped = OrderedDict()
	for show in shows:
		theater_info = theaters.get(show.theater, {})
		screen_info = screens.get(show.screen, {})

		theater_key = show.theater or "Unknown"
		theater_label = theater_info.get("theater_name", theater_key)
		theater_city = theater_info.get("city", "")

		if theater_key not in grouped:
			grouped[theater_key] = {
				"name": theater_label,
				"city": theater_city,
				"dates": OrderedDict(),
			}

		date_key = str(show.show_date)
		if date_key not in grouped[theater_key]["dates"]:
			grouped[theater_key]["dates"][date_key] = {
				"date": show.show_date,
				"date_formatted": frappe.utils.formatdate(show.show_date, "EEEE, d MMM yyyy"),
				"shows": [],
			}

		grouped[theater_key]["dates"][date_key]["shows"].append({
			"name": show.name,
			"start_time": frappe.utils.format_time(show.start_time, "hh:mm a"),
			"screen_name": screen_info.get("screen_name", ""),
			"screen_type": screen_info.get("screen_type", "Standard"),
			"ticket_price": show.ticket_price,
			"available_seats": show.available_seats,
			"total_seats": show.total_seats,
		})

	context.grouped_shows = grouped
	context.has_shows = len(shows) > 0
