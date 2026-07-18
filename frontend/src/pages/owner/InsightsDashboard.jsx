import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { format, addDays, addWeeks, addMonths, startOfMonth, getWeek, startOfWeek } from "date-fns";
import { toast } from "sonner";
import { ChevronLeft, ChevronRight, RotateCcw, IndianRupee, BarChart3, Users, Scissors, Calendar as CalendarIcon } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { API, ownerAuthConfig, money, formatRangeDisplay, STATUS_LABELS, PERIOD_OPTIONS, PERIOD_KPI_LABELS } from "./utils";
import { MetricCard, RankedList } from "./ui";

/**
 * Compute the "Week N" of the anchor date's month, where the first Monday of
 * the month counts as Week 1 and every subsequent Monday increments the count.
 * Matches the backend's `_revenue_period_bounds` implementation.
 */
function weekOfMonth(anchor) {
  const firstOfMonth = startOfMonth(anchor);
  const firstMonday = startOfWeek(firstOfMonth, { weekStartsOn: 1 });
  const anchorMonday = startOfWeek(anchor, { weekStartsOn: 1 });
  const diffDays = Math.round((anchorMonday - firstMonday) / (24 * 60 * 60 * 1000));
  return Math.floor(diffDays / 7) + 1;
}

/** Big, human-friendly "selected period" title per the product spec. */
function highlightLabel(period, anchor, customRange) {
  if (period === "day") return `${format(anchor, "d MMMM yyyy")} • ${format(anchor, "EEEE")}`;
  if (period === "week") return `${format(anchor, "MMMM yyyy")} • Week ${weekOfMonth(anchor)}`;
  if (period === "month") return format(anchor, "MMMM yyyy");
  if (period === "custom") {
    if (!customRange?.from || !customRange?.to) return "Pick a start and end date";
    if (format(customRange.from, "yyyy-MM-dd") === format(customRange.to, "yyyy-MM-dd")) return format(customRange.from, "d MMMM yyyy");
    return `${format(customRange.from, "d MMM yyyy")} — ${format(customRange.to, "d MMM yyyy")}`;
  }
  return "";
}

/**
 * Shared Insights panel used by BOTH the Owner Dashboard and the Manager Dashboard.
 *
 * Owner mode  → endpoint `/api/owner/revenue-insights`, salon selector via `salonId` prop
 * Manager mode → endpoint `/api/manager/revenue-insights`, salon auto-scoped by JWT
 */
export function InsightsDashboard({
  authToken,
  salonId,
  endpoint = "/owner/revenue-insights",
  titleEyebrow = "Revenue insights",
  titleMain = "Business pulse",
  testidPrefix = "insights",
  // Legacy prop compat — owner dashboard used to pass `ownerToken`.
  ownerToken,
}) {
  const token = authToken || ownerToken;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState("week");
  const [anchorDate, setAnchorDate] = useState(new Date());
  const [customRange, setCustomRange] = useState({ from: undefined, to: undefined });
  const [customPickerOpen, setCustomPickerOpen] = useState(false);

  const shiftPeriod = (direction) => {
    if (period === "custom") return;
    const delta = direction === "next" ? 1 : -1;
    setAnchorDate((current) => {
      if (period === "day") return addDays(current, delta);
      if (period === "week") return addWeeks(current, delta);
      return addMonths(current, delta);
    });
  };

  const load = useCallback(() => {
    if (!token) return;
    // For custom mode we need both bounds selected before hitting the API.
    if (period === "custom" && (!customRange.from || !customRange.to)) {
      setData(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const params = { period };
    if (period === "custom") {
      params.start_date = format(customRange.from, "yyyy-MM-dd");
      params.end_date = format(customRange.to, "yyyy-MM-dd");
    } else {
      params.anchor_date = format(anchorDate, "yyyy-MM-dd");
    }
    if (salonId) params.salon_id = salonId;
    axios.get(`${API}${endpoint}`, { params, headers: { Authorization: `Bearer ${token}` } })
      .then((r) => setData(r.data))
      .catch(() => toast.error("Could not load insights"))
      .finally(() => setLoading(false));
  }, [token, endpoint, salonId, period, anchorDate, customRange]);

  useEffect(() => { load(); }, [load]);

  const bigLabel = useMemo(() => highlightLabel(period, anchorDate, customRange), [period, anchorDate, customRange]);

  const rawChartData = data?.revenue_series || data?.revenue_by_weekday || [];
  const todayStr = format(new Date(), "yyyy-MM-dd");
  const chartData = rawChartData.filter((point) => period === "day" || !point.date || point.date < todayStr || data?.range?.end_date < todayStr);
  const statusItems = ["done", "cancelled", "no_show", "upcoming"];

  return (
    <div data-testid={`${testidPrefix}-panel`}>
      {/* Header + period controls */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">{titleEyebrow} · {data?.range?.label || "Selected period"}</p>
          <h2 className="font-serif text-3xl mt-1">{titleMain}</h2>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={period}
            onChange={(e) => {
              const nextPeriod = e.target.value;
              setPeriod(nextPeriod);
              if (nextPeriod !== "custom") setAnchorDate(new Date());
            }}
            data-testid={`${testidPrefix}-period-select`}
            className="h-10 rounded-none border border-stone-300 bg-white px-3 text-xs uppercase tracking-[0.15em] text-stone-700 focus:outline-none focus:border-stone-900"
          >
            {PERIOD_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          {period !== "custom" && (
            <>
              <button onClick={() => shiftPeriod("prev")} data-testid={`${testidPrefix}-period-prev`} className="inline-flex items-center gap-1 border border-stone-300 px-3 py-2 text-xs uppercase tracking-[0.15em] hover:border-stone-900 transition-colors"><ChevronLeft className="h-3 w-3" /> Previous</button>
              <button onClick={() => setAnchorDate(new Date())} data-testid={`${testidPrefix}-period-current`} className="border border-stone-300 px-3 py-2 text-xs uppercase tracking-[0.15em] hover:border-stone-900 transition-colors">Current</button>
              <button onClick={() => shiftPeriod("next")} data-testid={`${testidPrefix}-period-next`} className="inline-flex items-center gap-1 border border-stone-300 px-3 py-2 text-xs uppercase tracking-[0.15em] hover:border-stone-900 transition-colors">Next <ChevronRight className="h-3 w-3" /></button>
            </>
          )}
          {period === "custom" && (
            <Popover open={customPickerOpen} onOpenChange={setCustomPickerOpen}>
              <PopoverTrigger asChild>
                <button
                  data-testid={`${testidPrefix}-custom-range-trigger`}
                  className="inline-flex items-center gap-2 border border-stone-300 px-3 py-2 text-xs uppercase tracking-[0.15em] hover:border-stone-900 transition-colors bg-white"
                >
                  <CalendarIcon className="h-3 w-3" />
                  {customRange.from && customRange.to
                    ? `${format(customRange.from, "d MMM")} – ${format(customRange.to, "d MMM yyyy")}`
                    : "Pick range"}
                </button>
              </PopoverTrigger>
              <PopoverContent align="end" className="w-auto p-0">
                <Calendar
                  mode="range"
                  numberOfMonths={2}
                  selected={customRange}
                  onSelect={(r) => setCustomRange(r || { from: undefined, to: undefined })}
                  defaultMonth={customRange.from || new Date()}
                  data-testid={`${testidPrefix}-custom-range-calendar`}
                />
                <div className="flex items-center justify-between p-3 border-t border-stone-200 bg-stone-50">
                  <button
                    onClick={() => setCustomRange({ from: undefined, to: undefined })}
                    data-testid={`${testidPrefix}-custom-range-clear`}
                    className="text-xs uppercase tracking-[0.15em] text-stone-500 hover:text-stone-900"
                  >Clear</button>
                  <button
                    onClick={() => setCustomPickerOpen(false)}
                    disabled={!customRange.from || !customRange.to}
                    data-testid={`${testidPrefix}-custom-range-apply`}
                    className="border border-stone-900 bg-stone-900 text-white px-4 py-2 text-xs uppercase tracking-[0.15em] disabled:opacity-40"
                  >Apply</button>
                </div>
              </PopoverContent>
            </Popover>
          )}
          <button onClick={load} data-testid={`${testidPrefix}-refresh-button`} className="inline-flex items-center gap-2 border border-stone-300 px-3 py-2 text-xs uppercase tracking-[0.15em] hover:border-stone-900 transition-colors"><RotateCcw className="h-3 w-3" /> Refresh</button>
        </div>
      </div>

      {/* Prominent selected-period display */}
      <div className="border border-stone-200 bg-white px-5 py-4 mb-6 flex items-center gap-3" data-testid={`${testidPrefix}-selected-period`}>
        <span className="inline-flex items-center justify-center w-8 h-8 border border-stone-900 bg-stone-900 text-white">
          <CalendarIcon className="h-4 w-4" />
        </span>
        <div>
          <p className="text-[10px] uppercase tracking-[0.25em] text-stone-400">Viewing</p>
          <p className="font-serif text-xl leading-tight" data-testid={`${testidPrefix}-selected-period-label`}>{bigLabel}</p>
          {data?.range && period !== "custom" && (
            <p className="text-[11px] text-stone-500 mt-0.5">{formatRangeDisplay(data.range)}</p>
          )}
        </div>
      </div>

      {loading && <p className="text-sm text-stone-500" data-testid={`${testidPrefix}-loading`}>Loading…</p>}
      {!loading && !data && period === "custom" && (
        <p className="text-stone-500" data-testid={`${testidPrefix}-empty-custom`}>Pick a start and end date to see insights for that range.</p>
      )}
      {!loading && !data && period !== "custom" && (
        <p className="text-stone-500" data-testid={`${testidPrefix}-empty`}>No insights available.</p>
      )}

      {!loading && data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
            <MetricCard icon={IndianRupee} label={PERIOD_KPI_LABELS[period]} value={money(data.kpis.total_revenue)} testid={`${testidPrefix}-period-revenue`} />
            <MetricCard icon={BarChart3} label="Bookings" value={data.kpis.paid_booking_count} testid={`${testidPrefix}-period-bookings`} />
            <MetricCard icon={Users} label="Avg. booking" value={money(data.kpis.average_booking_value)} testid={`${testidPrefix}-average-booking`} />
          </div>

          <div className="space-y-6">
            {/* Status counts — moved ABOVE the revenue trend chart per spec */}
            <section className="border border-stone-200 bg-white p-6" data-testid={`${testidPrefix}-status-counts`}>
              <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-4">Status counts</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {statusItems.map((key) => (
                  <div key={key} className="flex items-center justify-between border border-stone-100 p-4" data-testid={`${testidPrefix}-status-${key}`}>
                    <span className="text-sm text-stone-600">{STATUS_LABELS[key]}</span>
                    <span className="font-serif text-2xl" data-testid={`${testidPrefix}-status-count-${key}`}>{data.status_counts[key] || 0}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="border border-stone-200 bg-white p-6" data-testid={`${testidPrefix}-weekday-chart`}>
              <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-4">
                <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Revenue trend by day</p>
                <p className="text-xs text-stone-400" data-testid={`${testidPrefix}-chart-period-label`}>{formatRangeDisplay(data.range)}</p>
              </div>
              <div className="h-[28rem]" data-testid={`${testidPrefix}-revenue-line-chart`}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 12, right: 18, left: 4, bottom: 18 }}>
                    <CartesianGrid stroke="#e7e5e4" strokeDasharray="4 4" vertical={false} />
                    <XAxis
                      dataKey="label"
                      tick={{ fontSize: 11, fill: "#78716c" }}
                      axisLine={{ stroke: "#d6d3d1" }}
                      tickLine={{ stroke: "#d6d3d1" }}
                      interval={period === "month" || (period === "custom" && chartData.length > 14) ? Math.max(0, Math.ceil(chartData.length / 10) - 1) : 0}
                    />
                    <YAxis
                      tickFormatter={(value) => money(value)}
                      tick={{ fontSize: 11, fill: "#78716c" }}
                      axisLine={{ stroke: "#d6d3d1" }}
                      tickLine={{ stroke: "#d6d3d1" }}
                      width={64}
                    />
                    <Tooltip formatter={(value) => [money(value), "Revenue"]} labelFormatter={(label, payload) => payload?.[0]?.payload?.date || label} />
                    <Line type="monotone" dataKey="revenue" stroke="#1c1917" strokeWidth={2.5} dot={{ r: 3, fill: "#1c1917" }} activeDot={{ r: 5 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            <div className="grid grid-cols-1 gap-6">
              <RankedList icon={Users} title="Revenue per stylist" rows={data.revenue_per_stylist} testid={`${testidPrefix}-stylist-revenue`} />
              <RankedList icon={Scissors} title="Revenue per service" rows={data.revenue_per_service} testid={`${testidPrefix}-service-revenue`} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
