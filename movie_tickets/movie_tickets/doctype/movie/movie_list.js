frappe.listview_settings["Movie"] = {
	add_fields: ["movie_status", "title", "language", "genre", "rating", "release_date"],
	get_indicator(doc) {
		const indicator_colors = {
			"Now Showing": "green",
			"Upcoming": "blue",
			"Ended": "gray",
		};
		const status = doc.movie_status || "Upcoming";

		return [__(status), indicator_colors[status] || "gray", `movie_status,=,${status}`];
	},
};
