import frappe


def get_context(context):
	slug = frappe.form_dict.get("slug")
	if not slug:
		frappe.throw("Movie not found", frappe.DoesNotExistError)

	movie = frappe.db.get_value(
		"Movie",
		{"slug": slug},
		["name", "title", "slug", "language", "genre", "duration_minutes", "rating", "poster", "director", "synopsis", "release_date", "movie_status", "movie_cast", "trailer_url"],
		as_dict=True,
	)

	if not movie:
		frappe.throw("Movie not found", frappe.DoesNotExistError)

	context.movie = movie
	context.title = movie.title
	context.no_cache = 1
