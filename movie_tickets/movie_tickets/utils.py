import frappe
from frappe.utils import today, formatdate, fmt_money


def send_daily_revenue_digest():
	"""Daily at 11 PM: send revenue digest email to Cinema Managers."""
	current_date = today()
	date_label = formatdate(current_date, "EEEE, d MMMM yyyy")

	# Today's confirmed/completed bookings
	stats = frappe.db.sql("""
		SELECT
			COUNT(*) as total_bookings,
			COALESCE(SUM(total_amount), 0) as total_revenue,
			COALESCE(SUM(number_of_seats), 0) as total_seats
		FROM `tabTicket Booking`
		WHERE DATE(booking_time) = %s
			AND booking_status IN ('Confirmed', 'Pending')
			AND docstatus != 2
	""", (current_date,), as_dict=True)[0]

	# Top movie by revenue today
	top_movie = frappe.db.sql("""
		SELECT
			movie_title,
			COUNT(*) as bookings,
			SUM(total_amount) as revenue
		FROM `tabTicket Booking`
		WHERE DATE(booking_time) = %s
			AND booking_status IN ('Confirmed', 'Pending')
			AND docstatus != 2
		GROUP BY movie_title
		ORDER BY revenue DESC
		LIMIT 1
	""", (current_date,), as_dict=True)

	top_movie_name = top_movie[0].movie_title if top_movie else "N/A"
	top_movie_revenue = fmt_money(top_movie[0].revenue, currency="INR") if top_movie else "₹0"
	top_movie_bookings = top_movie[0].bookings if top_movie else 0

	# Build HTML email
	html = f"""
	<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
		<h2 style="color: #1f2937; margin-bottom: 4px;">Daily Revenue Digest</h2>
		<p style="color: #6b7280; margin-top: 0;">{date_label}</p>

		<table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
			<tr>
				<td style="padding: 16px; background: #eff6ff; border-radius: 8px; text-align: center; width: 33%;">
					<div style="font-size: 28px; font-weight: 700; color: #1d4ed8;">{stats.total_bookings}</div>
					<div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;">Bookings</div>
				</td>
				<td style="width: 12px;"></td>
				<td style="padding: 16px; background: #f0fdf4; border-radius: 8px; text-align: center; width: 33%;">
					<div style="font-size: 28px; font-weight: 700; color: #16a34a;">{fmt_money(stats.total_revenue, currency="INR")}</div>
					<div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;">Revenue</div>
				</td>
				<td style="width: 12px;"></td>
				<td style="padding: 16px; background: #fefce8; border-radius: 8px; text-align: center; width: 33%;">
					<div style="font-size: 28px; font-weight: 700; color: #ca8a04;">{stats.total_seats}</div>
					<div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;">Seats Sold</div>
				</td>
			</tr>
		</table>

		<div style="padding: 16px; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; margin-top: 16px;">
			<div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">Top Movie</div>
			<div style="font-size: 18px; font-weight: 600; color: #1f2937; margin-top: 4px;">{top_movie_name}</div>
			<div style="font-size: 14px; color: #6b7280; margin-top: 2px;">{top_movie_bookings} bookings &middot; {top_movie_revenue}</div>
		</div>
	</div>
	"""

	# Get Cinema Manager emails
	recipients = get_cinema_manager_emails()
	if not recipients:
		return

	frappe.sendmail(
		recipients=recipients,
		subject=f"Daily Revenue Digest - {date_label}",
		message=html,
		now=True,
	)


def get_cinema_manager_emails():
	"""Get email addresses of users with Cinema Manager role."""
	return frappe.get_all(
		"Has Role",
		filters={"role": "Cinema Manager", "parenttype": "User"},
		fields=["parent"],
		pluck="parent",
	)
