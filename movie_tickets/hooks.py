app_name = "movie_tickets"
app_title = "Movie Tickets"
app_publisher = "Renish Ponkiya"
app_description = "Book Movie Tickets Platform"
app_email = "ponkiyarenish@gmail.com"
app_license = "mit"

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

# Website
website_route_rules = [
    {"from_route": "/movie/<slug>", "to_route": "movie"},
]