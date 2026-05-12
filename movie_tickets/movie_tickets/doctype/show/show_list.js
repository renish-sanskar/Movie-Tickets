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

	onload(listview) {
		if (frappe.user.has_role("Cinema Manager") || frappe.user.has_role("System Manager")) {
			listview.page.add_inner_button(__("Bulk Create Shows"), () => {
				show_bulk_create_dialog();
			});
		}
	},
};

function show_bulk_create_dialog() {
	// fetch screens first, then build dialog
	frappe.xcall("frappe.client.get_list", {
		doctype: "Screen",
		filters: { is_active: 1 },
		fields: ["name", "screen_name", "theater"],
		limit_page_length: 0,
		order_by: "theater asc, screen_name asc",
	}).then((screens) => {
		const screen_options = screens.map(
			(s) => ({ label: `${s.theater} — ${s.screen_name}`, value: s.name })
		);

		const time_options = [
			"09:00", "10:00", "11:00", "12:00", "13:00", "14:00",
			"15:00", "16:00", "17:00", "18:00", "18:30", "19:00",
			"20:00", "21:00", "22:00", "23:00",
		].map((t) => {
			const [h, m] = t.split(":");
			const hr = parseInt(h);
			const ampm = hr >= 12 ? "PM" : "AM";
			const h12 = hr > 12 ? hr - 12 : hr === 0 ? 12 : hr;
			return { label: `${h12}:${m} ${ampm}`, value: t };
		});

		const d = new frappe.ui.Dialog({
			title: __("Bulk Create Shows"),
			size: "large",
			fields: [
				{
					fieldname: "movie",
					label: __("Movie"),
					fieldtype: "Link",
					options: "Movie",
					reqd: 1,
					get_query: () => ({
						filters: { movie_status: ["!=", "Ended"] },
					}),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "ticket_price",
					label: __("Ticket Price (optional)"),
					fieldtype: "Currency",
					description: __("Leave blank to use each screen's base price"),
				},
				{ fieldtype: "Section Break", label: __("Date Range") },
				{
					fieldname: "from_date",
					label: __("From Date"),
					fieldtype: "Date",
					reqd: 1,
					default: frappe.datetime.get_today(),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "to_date",
					label: __("To Date"),
					fieldtype: "Date",
					reqd: 1,
					default: frappe.datetime.add_days(frappe.datetime.get_today(), 6),
				},
				{ fieldtype: "Section Break", label: __("Screens") },
				{
					fieldname: "screens",
					label: __("Select Screens"),
					fieldtype: "MultiCheck",
					options: screen_options,
					columns: 2,
				},
				{ fieldtype: "Section Break", label: __("Show Times") },
				{
					fieldname: "show_times",
					label: __("Select Show Times"),
					fieldtype: "MultiCheck",
					options: time_options,
					columns: 4,
				},
				{
					fieldname: "summary_html",
					fieldtype: "HTML",
					options: "<p class='text-muted'>" + __("Fill all fields to see summary.") + "</p>",
				},
			],
			primary_action_label: __("Create Shows"),
			primary_action(values) {
				const sel_screens = d.fields_dict.screens.get_checked_options();
				const sel_times = d.fields_dict.show_times.get_checked_options();

				if (!sel_screens.length) {
					frappe.throw(__("Select at least one screen"));
					return;
				}
				if (!sel_times.length) {
					frappe.throw(__("Select at least one show time"));
					return;
				}
				if (!values.from_date || !values.to_date) {
					frappe.throw(__("Date range is required"));
					return;
				}

				d.disable_primary_action();
				frappe.xcall("movie_tickets.api.bulk_create_shows", {
					movie: values.movie,
					screens: JSON.stringify(sel_screens),
					from_date: values.from_date,
					to_date: values.to_date,
					show_times: JSON.stringify(sel_times),
					ticket_price: values.ticket_price || null,
				}).then(() => {
					d.hide();
				}).catch(() => {
					d.enable_primary_action();
				});
			},
		});

		// live summary update
		const update_summary = () => {
			const sel_screens = d.fields_dict.screens.get_checked_options();
			const sel_times = d.fields_dict.show_times.get_checked_options();
			const from = d.get_value("from_date");
			const to = d.get_value("to_date");
			if (!from || !to || !sel_screens.length || !sel_times.length) return;

			const days = frappe.datetime.get_diff(to, from) + 1;
			if (days <= 0) return;

			const total = sel_screens.length * sel_times.length * days;
			d.fields_dict.summary_html.$wrapper.html(
				`<p class="text-muted"><strong>${total}</strong> shows will be created
				(${sel_screens.length} screen${sel_screens.length > 1 ? "s" : ""}
				&times; ${sel_times.length} time${sel_times.length > 1 ? "s" : ""}
				&times; ${days} day${days > 1 ? "s" : ""}).</p>`
			);
		};

		d.$wrapper.on("change", "input", update_summary);
		d.show();
	});
}