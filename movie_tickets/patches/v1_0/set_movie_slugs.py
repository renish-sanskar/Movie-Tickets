import frappe

from movie_tickets.movie_tickets.doctype.movie.movie import make_slug


def execute():
	"""Generate slug from title for all Movies where slug is NULL or empty."""

	movies = frappe.db.get_all(
		"Movie",
		filters=[["slug", "in", [None, ""]]],
		fields=["name", "title"],
	)

	for movie in movies:
		slug = make_slug(movie.title)
		frappe.db.set_value("Movie", movie.name, "slug", slug, update_modified=False)

	frappe.db.commit()
	frappe.msgprint(f"Set slugs for {len(movies)} movies.")
