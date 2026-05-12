frappe.listview_settings["Show"] = {
	add_fields: ["movie_title", "screen", "show_date", "start_time", "available_seats", "show_status"],
	get_indicator(doc) {
		const indicator_colors = {
			"Scheduled": "green",
			"Now Playing": "orange",
			"Completed": "gray",
			"Cancelled": "red",
		};
		const status = doc.show_status || "Scheduled";

		return [__(status), indicator_colors[status] || "gray", `show_status,=,${status}`];
	},
};