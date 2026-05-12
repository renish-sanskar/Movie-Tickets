frappe.pages["cinema-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Cinema Dashboard",
		single_column: true,
	});

	page.main.html(`
		<div class="cinema-dashboard" style="padding: 15px;">
			<div class="row">
				<div class="col-md-6">
					<div class="frappe-card p-4 mb-4">
						<h5 class="mb-3">Today's Occupancy by Theater</h5>
						<div id="chart-occupancy"></div>
						<p class="text-muted small mt-2 occupancy-empty d-none">No shows scheduled today.</p>
					</div>
				</div>
				<div class="col-md-6">
					<div class="frappe-card p-4 mb-4">
						<h5 class="mb-3">Top 5 Movies by Bookings</h5>
						<div id="chart-top-movies"></div>
						<p class="text-muted small mt-2 top-movies-empty d-none">No booking data yet.</p>
					</div>
				</div>
			</div>
			<div class="row">
				<div class="col-md-12">
					<div class="frappe-card p-4 mb-4">
						<h5 class="mb-3">30-Day Revenue Trend</h5>
						<div id="chart-revenue"></div>
					</div>
				</div>
			</div>
			<div class="row">
				<div class="col-md-12">
					<div class="frappe-card p-4 mb-4">
						<h5 class="mb-3">Bookings by Time Slot</h5>
						<div id="chart-timeslot"></div>
						<p class="text-muted small mt-2 timeslot-empty d-none">No booking data yet.</p>
					</div>
				</div>
			</div>
		</div>
	`);

	const PATH = "movie_tickets.movie_tickets.page.cinema_dashboard.cinema_dashboard";

	// ── Occupancy Bar Chart ──────────────────────────────────────────────
	frappe.xcall(`${PATH}.get_occupancy_by_theater`).then((r) => {
		if (!r.labels.length) {
			page.main.find(".occupancy-empty").removeClass("d-none");
			return;
		}
		new frappe.Chart("#chart-occupancy", {
			type: "bar",
			height: 280,
			colors: ["#7cd6fd", "#e2e2e2"],
			data: {
				labels: r.labels,
				datasets: [
					{ name: "Booked", values: r.booked },
					{ name: "Available", values: r.total.map((t, i) => Math.max(0, t - r.booked[i])) },
				],
			},
			barOptions: { stacked: true },
			tooltipOptions: {
				formatTooltipY: (d) => d + " seats",
			},
		});
	});

	// ── Revenue Trend Line Chart ─────────────────────────────────────────
	frappe.xcall(`${PATH}.get_revenue_trend`).then((r) => {
		new frappe.Chart("#chart-revenue", {
			type: "line",
			height: 280,
			colors: ["#743ee2"],
			data: {
				labels: r.labels,
				datasets: [{ name: "Revenue", values: r.values }],
			},
			lineOptions: { regionFill: 1, hideDots: 0 },
			tooltipOptions: {
				formatTooltipY: (d) => format_currency(d, "INR"),
			},
		});
	});

	// ── Bookings by Time Slot (Bar/Histogram) ────────────────────────────
	frappe.xcall(`${PATH}.get_bookings_by_time_slot`).then((r) => {
		if (!r.labels.length) {
			page.main.find(".timeslot-empty").removeClass("d-none");
			return;
		}
		new frappe.Chart("#chart-timeslot", {
			type: "bar",
			height: 280,
			colors: ["#ff6f61"],
			data: {
				labels: r.labels,
				datasets: [{ name: "Bookings", values: r.values }],
			},
			tooltipOptions: {
				formatTooltipY: (d) => d + " bookings",
			},
		});
	});

	// ── Top 5 Movies Donut Chart ─────────────────────────────────────────
	frappe.xcall(`${PATH}.get_top_movies`).then((r) => {
		if (!r.labels.length) {
			page.main.find(".top-movies-empty").removeClass("d-none");
			return;
		}
		new frappe.Chart("#chart-top-movies", {
			type: "donut",
			height: 280,
			colors: ["#7cd6fd", "#743ee2", "#ff6f61", "#ffa00a", "#47cfd1"],
			data: {
				labels: r.labels,
				datasets: [{ values: r.values }],
			},
		});
	});
};
