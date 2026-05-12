// Copyright (c) 2026, Renish Ponkiya and contributors
// For license information, please see license.txt

frappe.query_reports["Box Office Collection Report"] = {
	filters: [
		{
			fieldname: "theater",
			label: __("Theater"),
			fieldtype: "Link",
			options: "Theater",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
		{
			fieldname: "genre",
			label: __("Genre"),
			fieldtype: "Link",
			options: "Movie Genre",
		},
		{
			fieldname: "language",
			label: __("Language"),
			fieldtype: "Select",
			options: "\nEnglish\nHindi\nGujarati\nTamil\nTelugu\nOther",
		},
		{
			fieldname: "chart_type",
			label: __("Chart"),
			fieldtype: "Select",
			options: "Top 10 Movies by Revenue\nRevenue by Screen Type",
			default: "Top 10 Movies by Revenue",
		},
	],
};
