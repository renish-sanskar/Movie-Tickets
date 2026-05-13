/*
 * Movie Tickets – Global Script
 * Loaded via app_include_js in hooks.py (runs on every desk page).
 */

console.log("Movie Tickets App Loaded");

// Ctrl+Shift+B → open a new Ticket Booking form
frappe.ui.keys.add_shortcut({
	shortcut: "ctrl+shift+b",
	action: () => frappe.new_doc("Ticket Booking"),
	description: "New Ticket Booking",
	page: frappe.pages[""],  // global – works on any page
});
