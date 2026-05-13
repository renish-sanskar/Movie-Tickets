app_name = "movie_tickets"
app_title = "Movie Tickets"
app_publisher = "Renish Ponkiya"
app_description = "Book Movie Tickets Platform"
app_email = "ponkiyarenish@gmail.com"
app_license = "mit"

# Assets
app_include_css = "/assets/movie_tickets/css/cinema.css"
app_include_js = "/assets/movie_tickets/js/cinema.js"

# Exporting Custom Fields and Property Setters (for sort order)
fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", ["Cinema Manager", "Box Office Staff", "Customer"]]]
    },
    {
        "dt": "Custom DocPerm",
        "filters": [["parent", "in", ["Movie", "Movie Genre", "Theater", "Screen", "Show", "Ticket Booking", "Booking Configuration"]]]
    },
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Movie Tickets"]]
    },
    {
        "dt": "Property Setter",
        "filters": [["module", "=", "Movie Tickets"]]
    }
]

permission_query_conditions = {
    "Ticket Booking": "movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.get_permission_query_conditions"
}

# Doc Events
doc_events = {
    "Ticket Booking": {
        "after_insert": "movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.send_booking_received_email",
        "on_submit": "movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.send_booking_confirmation_email",
    },
}

# Website
website_route_rules = [
    {"from_route": "/movie/<slug>", "to_route": "movie"},
]

# Scheduler
scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "movie_tickets.movie_tickets.doctype.ticket_booking.ticket_booking.auto_expire_unpaid_bookings",
        ],
        "0 23 * * *": [
            "movie_tickets.movie_tickets.utils.send_daily_revenue_digest",
        ],
    },
    "daily": [
        "movie_tickets.movie_tickets.doctype.movie.movie.update_movie_statuses",
    ],
    "hourly": [
        "movie_tickets.movie_tickets.doctype.show.show.update_show_statuses",
    ],
}

# ──────────────────────────────────────────────────────────────────────────────
# override_whitelisted_methods (Concept Demo)
# ──────────────────────────────────────────────────────────────────────────────
#
# What it does:
#   Replaces a built-in Frappe whitelisted API with your own function.
#   When any client calls the original API path, Frappe routes it to your
#   override instead. The original function is NOT called unless you
#   explicitly call it from your wrapper.
#
# Use cases:
#   - Add logging/auditing to built-in APIs (e.g., track who queries what)
#   - Add extra validation or permission checks before a standard API runs
#   - Modify the return value of a standard API (e.g., filter out fields)
#   - Rate-limit or restrict access to specific APIs
#
# Risks:
#   - Breaks if Frappe changes the original function's signature in an upgrade
#   - Other apps expecting the original behavior may break silently
#   - Debugging is harder — the override is invisible at the call site
#   - Only ONE app can override a given method (last app in apps.txt wins)
#
# When to use vs alternatives:
#   - Use override_whitelisted_methods when you MUST intercept the exact API
#     path that the client already calls (e.g., frappe.client.get_count).
#   - Prefer doc_events / controller hooks for document lifecycle logic.
#   - Prefer custom whitelisted methods for new functionality.
#   - Prefer permission_query_conditions / has_permission for access control.
#
# ──────────────────────────────────────────────────────────────────────────────
override_whitelisted_methods = {
    "frappe.client.get_count": "movie_tickets.movie_tickets.overrides.get_count_with_logging",
}