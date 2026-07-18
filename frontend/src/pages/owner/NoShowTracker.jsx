import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { format } from "date-fns";
import { toast } from "sonner";
import { RotateCcw } from "lucide-react";
import { API, ownerAuthConfig, to12h } from "./utils";
import { MetricCard } from "./ui";

export function NoShowTracker({ ownerToken, salonId }) {
  const [month, setMonth] = useState(() => format(new Date(), "yyyy-MM"));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!ownerToken) return;
    setLoading(true);
    const params = { month };
    if (salonId) params.salon_id = salonId;
    axios.get(`${API}/owner/no-shows`, { params, ...ownerAuthConfig(ownerToken) })
      .then((r) => setData(r.data))
      .catch(() => toast.error("Could not load no-shows"))
      .finally(() => setLoading(false));
  }, [ownerToken, month, salonId]);

  useEffect(() => { load(); }, [load]);

  return (
    <div data-testid="owner-noshow-panel">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Monthly no-show report</p>
          <h2 className="font-serif text-3xl mt-1">Missed appointments</h2>
        </div>
        <div className="flex gap-2">
          <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} data-testid="noshow-month-input" className="border border-stone-300 bg-white px-3 py-2 text-sm" />
          <button onClick={load} data-testid="noshow-refresh-button" className="inline-flex items-center gap-2 border border-stone-300 px-3 py-2 text-xs uppercase tracking-[0.15em] hover:border-stone-900 transition-colors"><RotateCcw className="h-3 w-3" /> Refresh</button>
        </div>
      </div>

      {loading && <p className="text-sm text-stone-500" data-testid="noshow-loading">Loading…</p>}
      {!loading && data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            <MetricCard label="No-show rate" value={`${data.no_show_rate.toFixed(1)}%`} testid="noshow-rate" />
            <MetricCard label="No-shows" value={data.total_no_shows} testid="noshow-total" />
            <MetricCard label="Repeat flags" value={data.repeat_customers} testid="noshow-repeat-total" tone={data.repeat_customers > 0 ? "danger" : "neutral"} />
          </div>

          {data.no_shows.length === 0 ? (
            <p className="text-stone-500" data-testid="noshow-empty">No no-shows recorded for this month.</p>
          ) : (
            <div className="space-y-3" data-testid="noshow-list">
              {data.no_shows.map((b) => (
                <article key={b.id} data-testid={`noshow-row-${b.id}`} className={`border p-5 bg-white ${b.repeat_no_show ? "border-rose-500" : "border-stone-200"}`}>
                  <div className="flex flex-col md:flex-row md:items-center gap-4">
                    <div className="md:w-36">
                      <p className="font-serif text-xl" data-testid={`noshow-date-${b.id}`}>{format(new Date(`${b.date}T00:00:00`), "d MMM")}</p>
                      <p className="text-xs text-stone-500" data-testid={`noshow-time-${b.id}`}>{to12h(b.start_time)}</p>
                    </div>
                    <div className="flex-grow">
                      <p className="font-serif text-lg" data-testid={`noshow-customer-${b.id}`}>{b.customer_name} <span className="text-sm text-stone-500 font-sans">· {b.customer_phone}</span></p>
                      <p className="text-sm text-stone-500" data-testid={`noshow-details-${b.id}`}>{b.service?.name} · with {b.stylist?.name}</p>
                    </div>
                    <div className="flex flex-col items-start md:items-end gap-2">
                      <span data-testid={`noshow-count-${b.id}`} className={`inline-block px-3 py-1 text-xs uppercase tracking-[0.15em] border ${b.repeat_no_show ? "border-rose-500 bg-rose-50 text-rose-800" : "border-stone-300 bg-stone-50 text-stone-700"}`}>{b.customer_no_show_count} no-show{b.customer_no_show_count === 1 ? "" : "s"}</span>
                      {b.repeat_no_show && <span data-testid={`noshow-repeat-flag-${b.id}`} className="text-xs uppercase tracking-[0.2em] text-rose-700">Repeat no-show</span>}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
