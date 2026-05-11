app_name = "movie_tickets"
app_title = "Movie Tickets"
app_publisher = "Renish Ponkiya"
app_description = "Book Movie Tickets Platform"
app_email = "ponkiyarenish@gmail.com"
app_license = "mit"

# Exporting Custom Fields and Property Setters (for sort order)
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Movie Tickets"]]
    },
    {
        "dt": "Property Setter",
        "filters": [["module", "=", "Movie Tickets"]]
    }
]