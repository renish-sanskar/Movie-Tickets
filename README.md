# Movie Tickets

A Frappe (v16) app for cinema management and online movie ticket booking. Manage theaters, screens, movies, shows, and bookings — with a public website for customers, a dashboard for cinema staff, role-based access control, automated email notifications, and a tiered refund policy.

## Setup Instructions

### Prerequisites

- Python 3.14+
- Frappe Bench (v16)
- MariaDB / PostgreSQL
- Redis, Node.js (as required by Frappe)

### Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app <repo-url> --branch version-16
bench install-app movie_tickets
bench --site <site-name> migrate
```

### Development

```bash
cd apps/movie_tickets
pre-commit install   # ruff, eslint, prettier, pyupgrade
```

### Python Dependencies

- `qrcode[pil]~=8.0` — QR code generation for ticket print formats.

---

## DocTypes

| DocType | Type | Naming | Description |
|---------|------|--------|-------------|
| **Movie** | Document | `MOV-.#####` | Movie master — title, slug, genre, language, duration, release/end dates, rating, director, cast, synopsis, poster, trailer URL, status. |
| **Movie Genre** | Document | `field:genre_name` | Genre master (Action, Drama, etc.). |
| **Theater** | Document | Auto | Cinema/theater — name, city, address, phone, active flag, computed `total_screens`. |
| **Screen** | Document | Auto | Screen within a theater — name, type (Standard/IMAX/3D/4DX), seat layout (`seat_rows` × `seats_per_row`), `base_price`, active flag. |
| **Show** | Document | `SHW-.YYYY.-.#####` | A scheduled movie showing — links Movie + Screen, date/time, ticket price, `total_seats`, `booked_seats`, `available_seats`, status (Scheduled/Now Playing/Completed/Cancelled). |
| **Ticket Booking** | Submittable | `BKG-.YYYY.-.#####` | Booking record — links Show, customer info, seats (child table), totals, payment status, booking status (Pending → Confirmed / Cancelled / Expired), refund amount, cancellation reason. |
| **Booked Seat** | Child Table | — | Individual seat in a booking — `seat_label` (e.g. `A-12`), `row_letter`, `seat_number`, `seat_price`. |
| **Booking Configuration** | Single | — | Global settings — `max_seats_per_booking`, `booking_expiry_minutes`, `full_refund_hours`, `partial_refund_hours`, `partial_refund_pct`, `enable_auto_expiry`, `booking_open_days_before`. |

### Roles

| Role | Access |
|------|--------|
| **Cinema Manager** | Full CRUD on all DocTypes. |
| **Box Office Staff** | Full CRUD on all DocTypes. |
| **Customer** | Can create bookings; can only read/write own bookings. |

---

## Website Pages

| Route | File | Description |
|-------|------|-------------|
| `/now-showing` | `www/now-showing.html` | Public listing of currently showing movies. |
| `/movie/<slug>` | `www/movie.html` | Public movie detail page (routed via `website_route_rules`). |
| `/movie-shows` | `www/movie-shows.html` | Shows for a selected movie, filterable by city/date. |
| `/select-seats` | `www/select-seats.html` | Seat selection grid for a specific show. |
| `/my-bookings` | `www/my-bookings.html` | Logged-in customer's booking history. |

---

## Page & Report

| Type | Name | Description |
|------|------|-------------|
| **Page** | Cinema Dashboard (`/app/cinema-dashboard`) | Staff-only dashboard with occupancy by theater, revenue trend (30 days), booking status breakdown, and upcoming shows. |
| **Script Report** | Box Office Collection Report | Aggregated revenue by movie with genre/language filters, chart, and summary cards. |
| **Print Format** | Movie Ticket | Custom print format for Ticket Booking with QR code. |

---

## API Reference

Base path: `/api/method/movie_tickets.api.<method>`

| Method | Auth | Parameters | Returns |
|--------|------|------------|---------|
| `get_seat_availability` | Logged in | `show_name` | `{ total_rows, seats_per_row, seats[][] }` — each seat has `seat_label` and `status` (available/booked). |
| `create_booking` | Logged in | `show`, `customer_name`, `customer_email`, `customer_phone`, `seats` (JSON array of `{seat_label}`) | `{ success, booking_name, total_amount, message }` |
| `get_shows_for_movie` | Guest OK | `movie`, `city` (optional), `date` (optional) | List of shows with theater, screen type, date, time, price, available seats. |
| `send_booking_confirmation` | Logged in | `booking_name` | `{ success, booking_name, message }` — sends HTML email to customer. |

### Cinema Dashboard APIs

Base path: `/api/method/movie_tickets.movie_tickets.page.cinema_dashboard.cinema_dashboard.<method>`

| Method | Description |
|--------|-------------|
| `get_occupancy_by_theater` | Today's booked vs total seats per theater. |
| `get_revenue_trend` | Daily revenue for the last 30 days. |

---

## Hooks & Automation

### Doc Events

| DocType | Event | Action |
|---------|-------|--------|
| Ticket Booking | `after_insert` | Send "booking received" email to customer. |
| Ticket Booking | `on_submit` | Send "booking confirmed" email to customer. |

### Scheduler Jobs

| Schedule | Job | Description |
|----------|----|-------------|
| Every 5 min | `auto_expire_unpaid_bookings` | Expires bookings still in Pending status past the configured expiry window. |
| Daily 11 PM | `send_daily_revenue_digest` | Emails daily revenue summary (bookings, revenue, seats sold, top movie) to Cinema Managers. |
| Daily | `update_movie_statuses` | Transitions movie status based on release/end dates. |
| Hourly | `update_show_statuses` | Transitions show status based on date/time. |

### Override

| Original Method | Override | Purpose |
|----------------|----------|---------|
| `frappe.client.get_count` | `get_count_with_logging` | Logs DocType, filters, and user for every `get_count` call (demo/audit). |

### Permission Query

| DocType | Condition |
|---------|-----------|
| Ticket Booking | Customers see only their own bookings (`booked_by = user`). |

### Cancellation & Refund Policy

Configured via Booking Configuration:
- **> `full_refund_hours` before show** → 100% refund.
- **≥ `partial_refund_hours` before show** → `partial_refund_pct`% refund.
- **< `partial_refund_hours` before show** → No refund.

### Fixtures

Exported via `bench export-fixtures`:
- Role (Cinema Manager, Box Office Staff, Customer)
- Custom DocPerm
- Custom Field
- Property Setter

---

## Data Migration Patches (v1.0)

Listed in `patches.txt` under `[post_model_sync]`. Run via `bench --site <site-name> migrate`.

| # | Patch | What it does |
|---|-------|--------------|
| 1 | `recalculate_show_seat_counts` | Recalculates `booked_seats` and `available_seats` for every Show by counting confirmed bookings (`docstatus=1`, `booking_status='Confirmed'`). |
| 2 | `set_movie_slugs` | Generates a URL-friendly `slug` from `title` for all Movies where slug is NULL or empty using `make_slug()`. |
| 3 | `populate_booking_source` | Creates the `custom_booking_source` Custom Field on Ticket Booking (options: Counter/Website/App, default: Website) and backfills `'Counter'` for all existing bookings where the field is NULL or empty. |

### Verify Patches

```bash
bench --site <site-name> mariadb -e "SELECT patch FROM \`tabPatch Log\` WHERE patch LIKE 'movie_tickets.patches%';"
```

---

## Testing

### Run All Tests

```bash
bench --site <site-name> run-tests --app movie_tickets
```

### Test Modules

| File | Coverage |
|------|----------|
| `test_ticket_booking.py` | Booking creation, totals, seat validation, duplicate seats, submit/cancel, refund calculations, seat availability, max-seats limit, show status validation. |
| `test_ticket_booking_permissions.py` | Role-based access — Customer sees only own bookings, Manager/Staff see all. Permission query conditions. |
| `test_api.py` | API endpoints — `get_seat_availability`, `create_booking`, `get_shows_for_movie`, `send_booking_confirmation`. |

### Manual Verification

```bash
# Seat counts
bench --site <site-name> mariadb -e "SELECT name, total_seats, booked_seats, available_seats FROM \`tabShow\` LIMIT 5;"

# Movie slugs
bench --site <site-name> mariadb -e "SELECT name, title, slug FROM \`tabMovie\`;"

# Booking source
bench --site <site-name> mariadb -e "SELECT name, custom_booking_source FROM \`tabTicket Booking\` LIMIT 5;"
```

---

## Assumptions

- Each booking is for a single show and a single customer.
- Seat layout is a fixed rectangular grid (`seat_rows` × `seats_per_row`); no irregular layouts.
- Payment is tracked via `payment_status` field — no built-in payment gateway integration.
- Email notifications (booking received, booking confirmed, daily digest) require SMTP to be configured in Frappe.
- `booking_open_days_before` in Booking Configuration controls how far in advance bookings open.
- Seats are labeled `<ROW_LETTER>-<SEAT_NUMBER>` (e.g. `A-1`, `B-12`).

## Limitations

- No payment gateway integration — `payment_status` is set on submit; extend for Razorpay/Stripe as needed.
- No seat-type pricing — all seats in a show use `ticket_price` from Show (or `base_price` from Screen); no premium/VIP tiers.
- No multi-language i18n for website pages or email templates.
- No recurring/subscription bookings.
- One Custom Field (`custom_booking_source`) is created via patch rather than being part of the core DocType schema.

---

## License

MIT
