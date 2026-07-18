import { useEffect, useState } from "react";
import axios from "axios";
import { format } from "date-fns";
import { ChevronLeft, ChevronRight, CheckCircle2, XCircle } from "lucide-react";
import { API, ownerAuthConfig, to12h, money, STATUS_STYLES, STATUS_LABELS } from "./utils";

export function DailyBook({ ownerToken, date, setDate, bookings, loading, onCancel, onSetStatus, salonId }) {
  return (
    <>
      <RevenueTrend ownerToken={ownerToken} salonId={salonId} />
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <h2 className="font-serif text-3xl" data-testid="owner-current-date">{format(date, "EEEE, d MMMM yyyy")}</h2>
        <div className="flex gap-2">
          <button data-testid="owner-date-prev-button" onClick={() => setDate(new Date(date.getTime() - 86400000))} className="border border-stone-300 px-3 py-2 hover:border-stone-900 transition-colors"><ChevronLeft className="h-4 w-4" /></button>
          <button data-testid="owner-date-today-button" onClick={() => setDate(new Date())} className="border border-stone-300 px-3 py-2 text-xs uppercase tracking-[0.15em] hover:border-stone-900 transition-colors">Today</button>
          <button data-testid="owner-date-next-button" onClick={() => setDate(new Date(date.getTime() + 86400000))} className="border border-stone-300 px-3 py-2 hover:border-stone-900 transition-colors"><ChevronRight className="h-4 w-4" /></button>
        </div>
      </div>

      {loading && <p className="text-sm text-stone-500" data-testid="owner-bookings-loading">Loading…</p>}
      {!loading && bookings.length === 0 && <p className="text-stone-500" data-testid="owner-empty">No bookings.</p>}

      <div className="space-y-3" data-testid="owner-bookings">
        {bookings.map((b) => (
          <article key={b.id} data-testid={`owner-booking-${b.id}`} className="grid grid-cols-1 md:grid-cols-[96px_1fr_auto_auto] gap-4 border border-stone-200 bg-white p-5 transition-colors hover:border-stone-300">
            <div>
              <p className="font-serif text-xl" data-testid={`owner-booking-time-${b.id}`}>{to12h(b.start_time)}</p>
              <p className="text-xs text-stone-500">{b.duration_min} min</p>
            </div>
            <div>
              <p className="font-serif text-lg" data-testid={`owner-booking-customer-${b.id}`}>{b.customer_name} <span className="text-sm text-stone-500 font-sans">· {b.customer_phone}</span></p>
              <p className="text-sm text-stone-500" data-testid={`owner-booking-details-${b.id}`}>{b.service?.name} · with {b.stylist?.name}</p>
              {b.no_show_followup_status && (
                <p className="text-xs text-rose-700 mt-1" data-testid={`owner-booking-followup-${b.id}`}>No-show follow-up: {b.no_show_followup_status}</p>
              )}
            </div>
            <div className="flex md:flex-col items-start md:items-end gap-2">
              <span data-testid={`owner-booking-status-${b.id}`} className={`inline-block px-3 py-1 text-xs uppercase tracking-[0.15em] border ${STATUS_STYLES[b.status]}`}>{STATUS_LABELS[b.status] || b.status}</span>
              <p className="font-serif text-lg" data-testid={`owner-booking-price-${b.id}`}>{money(b.service?.price || 0)}</p>
            </div>
            <div className="flex flex-wrap md:flex-col gap-2 md:items-stretch">
              <button onClick={() => onSetStatus(b, "done")} disabled={b.status === "done" || b.status === "cancelled"} data-testid={`owner-btn-done-${b.id}`} className="inline-flex items-center justify-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-900 hover:bg-stone-900 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"><CheckCircle2 className="h-3 w-3" /> Done</button>
              <button onClick={() => onSetStatus(b, "no_show")} disabled={b.status === "no_show" || b.status === "cancelled"} data-testid={`owner-btn-noshow-${b.id}`} className="inline-flex items-center justify-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-rose-500 hover:text-rose-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"><XCircle className="h-3 w-3" /> No-show</button>
              {b.status !== "cancelled" && b.status !== "done" && (
                <button onClick={() => onCancel(b)} data-testid={`btn-cancel-${b.id}`} className="px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-rose-500 hover:text-rose-700 transition-colors">Cancel</button>
              )}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function RevenueTrend({ ownerToken, salonId }) {
  const [series, setSeries] = useState([]);
  useEffect(() => {
    if (!ownerToken) return;
    const params = { days: 7 };
    if (salonId) params.salon_id = salonId;
    axios.get(`${API}/owner/revenue-trend`, { params, ...ownerAuthConfig(ownerToken) }).then((r) => setSeries(r.data.series)).catch(() => {});
  }, [ownerToken, salonId]);
  if (series.length === 0) return null;
  const max = Math.max(1, ...series.map((s) => s.revenue));
  const total = series.reduce((sum, s) => sum + s.revenue, 0);
  return (
    <div className="border border-stone-200 bg-white p-6 mb-8" data-testid="revenue-trend">
      <div className="flex items-end justify-between mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Revenue · Last 7 days</p>
          <p className="font-serif text-3xl mt-1" data-testid="trend-total">{money(total)}</p>
        </div>
        <p className="text-xs text-stone-500">{series.reduce((n, s) => n + s.count, 0)} bookings</p>
      </div>
      <div className="flex items-end gap-2 h-32">
        {series.map((s) => {
          const h = (s.revenue / max) * 100;
          return (
            <div key={s.date} className="flex-1 flex flex-col items-center justify-end gap-1" title={`${s.date}: ${money(s.revenue)}`} data-testid={`trend-day-${s.date}`}>
              <span className="text-[10px] text-stone-400" data-testid={`trend-day-revenue-${s.date}`}>{money(s.revenue)}</span>
              <div className="w-full bg-stone-900 transition-[height] duration-500" style={{ height: `${Math.max(2, h)}%` }} data-testid={`trend-day-bar-${s.date}`} />
              <span className="text-[10px] text-stone-500">{s.date.slice(5)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
