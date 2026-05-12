import frappe


def get_context(context):
	context.no_cache = 1
	context.title = "Now Showing"

	genre = frappe.form_dict.get("genre")
	language = frappe.form_dict.get("language")

	filters = {"movie_status": "Now Showing"}
	if genre:
		filters["genre"] = genre
	if language:
		filters["language"] = language

	context.movies = frappe.get_all(
		"Movie",
		filters=filters,
		fields=["name", "title", "slug", "language", "genre", "duration_minutes", "rating", "poster", "release_date"],
		order_by="release_date desc",
	)

	context.genres = frappe.get_all(
		"Movie Genre",
		filters={"is_active": 1},
		fields=["genre_name"],
		order_by="genre_name asc",
		pluck="genre_name",
	)

	context.languages = frappe.get_all(
		"Movie",
		filters={"movie_status": "Now Showing"},
		fields=["language"],
		distinct=True,
		order_by="language asc",
		pluck="language",
	)

	context.selected_genre = genre or ""
	context.selected_language = language or ""
