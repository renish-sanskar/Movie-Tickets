### Movie Tickets

Book Movie Tickets Platform

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch version-16
bench install-app movie_tickets
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/movie_tickets
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### Data Migration Patches (v1.0)

Run `bench --site <site-name> migrate` to execute all pending patches.

| # | Patch | Purpose |
|---|-------|---------|
| 1 | `recalculate_show_seat_counts` | Recalculates `booked_seats` and `available_seats` for all Shows by counting actual Confirmed bookings (docstatus=1, booking_status='Confirmed'). |
| 2 | `set_movie_slugs` | Generates URL-friendly `slug` from `title` for all Movies where slug is NULL or empty. |
| 3 | `populate_booking_source` | Sets `custom_booking_source = 'Counter'` for all existing bookings where the field is NULL or empty. |

**Verification:**

```bash
# Run patches
bench --site cinema.localhost migrate

# Verify patches executed
bench --site cinema.localhost mariadb -e "SELECT patch FROM \`tabPatch Log\` WHERE patch LIKE 'movie_tickets.patches%';"

# Verify seat counts
bench --site cinema.localhost mariadb -e "SELECT name, total_seats, booked_seats, available_seats FROM \`tabShow\` LIMIT 5;"

# Verify slugs
bench --site cinema.localhost mariadb -e "SELECT name, title, slug FROM \`tabMovie\`;"

# Verify booking source
bench --site cinema.localhost mariadb -e "SELECT name, custom_booking_source FROM \`tabTicket Booking\` LIMIT 5;"
```

### License

mit
