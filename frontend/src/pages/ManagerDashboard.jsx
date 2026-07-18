import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { format } from "date-fns";
import { toast } from "sonner";
import { LogOut, Calendar as CalendarIcon, Menu, X } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { API, to12h, STATUS_LABELS } from "./owner/utils";
import { MetricCard } from "./owner/ui";
import { InsightsDashboard } from "./owner/InsightsDashboard";
import SearchableSelect from "@/components/SearchableSelect";
import { getValidToken } from "../lib/authStore";
import { TodayView, CustomerSearchView, AvailabilityView, WorkingHoursView } from "./StylistPortal";

const managerAuth = (token) => ({ headers: { Authorization: `Bearer ${token}` } });
const money = (v) => `₹${Math.round(Number(v || 0)).toLocaleString("en-IN")}`;

const TABS = [
  { key: "daily", label: "Daily Book", description: "Appointments" },
  { key: "stylists", label: "Stylists", description: "Per-stylist view" },
  { key: "customers", label: "Customer Tracker", description: "History" },
  { key: "noshow", label: "No Show Tracker", description: "Missed visits" },
  { key: "insights", label: "Insights", description: "Revenue" },
];

export default function ManagerDashboard() {
  const navigate = useNavigate();
  const token = getValidToken("manager");
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("daily");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [date, setDate] = useState(new Date());
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { if (!token) navigate("/login", { replace: true }); }, [token, navigate]);

  useEffect(() => {
    if (!token) return;
    axios.get(`${API}/manager/me`, managerAuth(token))
      .then((r) => setMe(r.data))
      .catch(() => { localStorage.removeItem("manager_token"); navigate("/login", { replace: true }); });
  }, [token, navigate]);

  const dateStr = format(date, "yyyy-MM-dd");
  const load = useCallback(() => {
    if (!token) return;
    setLoading(true);
    axios.get(`${API}/manager/bookings`, { params: { date: dateStr }, ...managerAuth(token) })
      .then((r) => setBookings(r.data.bookings))
      .catch(() => toast.error("Could not load"))
      .finally(() => setLoading(false));
  }, [token, dateStr]);
  useEffect(() => { if (tab === "daily") load(); }, [tab, load]);

  const cancel = async (b) => {
    if (!window.confirm(`Cancel ${b.customer_name}'s ${to12h(b.start_time)} booking?`)) return;
    await axios.patch(`${API}/manager/bookings/${b.id}/cancel`, null, managerAuth(token));
    toast.success("Booking cancelled");
    load();
  };
  const setStatus = async (b, status) => {
    await axios.patch(`${API}/manager/bookings/${b.id}/status`, { status }, managerAuth(token));
    toast.success(`Marked ${STATUS_LABELS[status]}`);
    load();
  };
  const logout = () => { localStorage.removeItem("manager_token"); navigate("/login", { replace: true }); };

  if (!token || !me) return null;

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-[#FAF9F6]">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button onClick={() => setMobileOpen(true)} data-testid="manager-mobile-menu-open" className="lg:hidden border border-stone-300 p-2"><Menu className="h-4 w-4" /></button>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-stone-500" data-testid="manager-salon-name">{me.salon?.name || "Salon"}</p>
              <h1 className="font-serif text-2xl mt-1">Manager Dashboard</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs uppercase tracking-[0.2em] text-stone-500" data-testid="manager-name">Signed in as {me.manager?.name}</span>
            <button onClick={logout} data-testid="btn-manager-logout" className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-stone-600 hover:text-stone-900">
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-[240px_minmax(0,1fr)] gap-10">
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button className="absolute inset-0 bg-stone-950/30" onClick={() => setMobileOpen(false)} />
            <aside className="relative h-full w-72 max-w-[85vw] bg-white border-r border-stone-200 p-4 shadow-xl">
              <div className="flex items-center justify-between mb-6"><p className="text-xs uppercase tracking-[0.25em] text-stone-500">Menu</p><button onClick={() => setMobileOpen(false)} className="border border-stone-300 p-2"><X className="h-4 w-4" /></button></div>
              <ManagerNav tab={tab} setTab={(k) => { setTab(k); setMobileOpen(false); }} />
            </aside>
          </div>
        )}
        <aside className="hidden lg:block"><ManagerNav tab={tab} setTab={setTab} /></aside>
        <section className="min-w-0">
          {tab === "daily" && <ManagerDaily token={token} date={date} setDate={setDate} bookings={bookings} loading={loading} onCancel={cancel} onSetStatus={setStatus} />}
          {tab === "stylists" && <ManagerStylistsView token={token} salonId={me.salon?.id} />}
          {tab === "customers" && <ManagerCustomers token={token} />}
          {tab === "noshow" && <ManagerNoShow token={token} />}
          {tab === "insights" && <ManagerInsights token={token} />}
        </section>
      </main>
    </div>
  );
}

function ManagerNav({ tab, setTab }) {
  return (
    <nav className="space-y-2" data-testid="manager-nav">
      {TABS.map((item) => {
        const active = tab === item.key;
        return (
          <button key={item.key} type="button" onClick={() => setTab(item.key)} data-testid={`manager-tab-${item.key}`} className={`w-full text-left border px-3 py-3 ${active ? "border-stone-900 bg-stone-900 text-stone-50" : "border-stone-200 bg-white text-stone-700 hover:border-stone-900"}`}>
            <span className="block text-xs uppercase tracking-[0.16em]">{item.label}</span>
            <span className={`mt-1 block text-[11px] ${active ? "text-stone-300" : "text-stone-500"}`}>{item.description}</span>
          </button>
        );
      })}
    </nav>
  );
}

function ManagerDaily({ token, date, setDate, bookings, loading, onCancel, onSetStatus }) {
  return (
    <div data-testid="manager-daily-panel">
      <div className="grid grid-cols-1 xl:grid-cols-[300px_1fr] gap-8">
        <div>
          <div className="flex items-center gap-2 mb-3"><CalendarIcon className="h-4 w-4 text-stone-500" /><p className="text-xs uppercase tracking-[0.25em] text-stone-500">Day</p></div>
          <div className="border border-stone-200 bg-white p-3"><Calendar mode="single" selected={date} onSelect={(d) => d && setDate(d)} className="rounded-none" /></div>
        </div>
        <div>
          <h2 className="font-serif text-3xl mb-6" data-testid="manager-current-date">{format(date, "EEEE, d MMMM yyyy")}</h2>
          {loading && <p className="text-sm text-stone-500">Loading…</p>}
          {!loading && bookings.length === 0 && <p className="text-stone-500" data-testid="manager-empty">No bookings.</p>}
          <div className="space-y-3">
            {bookings.map((b) => (
              <article key={b.id} data-testid={`manager-booking-${b.id}`} className="grid grid-cols-1 md:grid-cols-[96px_1fr_auto_auto] gap-4 border border-stone-200 bg-white p-5">
                <div>
                  <p className="font-serif text-xl">{to12h(b.start_time)}</p>
                  <p className="text-xs text-stone-500">{b.duration_min} min</p>
                </div>
                <div>
                  <p className="font-serif text-lg">{b.customer_name} <span className="text-sm text-stone-500 font-sans">· {b.customer_phone}</span></p>
                  <p className="text-sm text-stone-500">{b.service?.name} · with {b.stylist?.name}</p>
                </div>
                <div className="flex md:flex-col items-start md:items-end gap-2">
                  <span className="inline-block px-3 py-1 text-xs uppercase tracking-[0.15em] border">{STATUS_LABELS[b.status] || b.status}</span>
                  <p className="font-serif text-lg">{money(b.service?.price || 0)}</p>
                </div>
                <div className="flex flex-wrap md:flex-col gap-2">
                  <button onClick={() => onSetStatus(b, "done")} disabled={b.status === "done" || b.status === "cancelled"} data-testid={`manager-btn-done-${b.id}`} className="px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-900 hover:bg-stone-900 hover:text-white disabled:opacity-40">Done</button>
                  <button onClick={() => onSetStatus(b, "no_show")} disabled={b.status === "no_show" || b.status === "cancelled"} data-testid={`manager-btn-noshow-${b.id}`} className="px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-rose-500 disabled:opacity-40">No-show</button>
                  {b.status !== "cancelled" && b.status !== "done" && <button onClick={() => onCancel(b)} data-testid={`manager-btn-cancel-${b.id}`} className="px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-rose-500">Cancel</button>}
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ManagerCustomers({ token }) {
  const [customers, setCustomers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [profile, setProfile] = useState(null);
  useEffect(() => {
    axios.get(`${API}/manager/customers/search`, managerAuth(token)).then((r) => {
      setCustomers(r.data.customers || []);
      setSelected((c) => c || r.data.customers?.[0]?.customer_phone || null);
    });
  }, [token]);
  useEffect(() => {
    if (!selected) return;
    axios.get(`${API}/manager/customers/${selected}`, managerAuth(token)).then((r) => setProfile(r.data));
  }, [selected, token]);
  const opts = customers.map((c) => ({ value: c.customer_phone, label: `${c.customer_name || "Customer"} · ${c.customer_phone}` }));
  return (
    <div data-testid="manager-customers-panel">
      <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Client history</p>
      <h2 className="font-serif text-3xl mt-1 mb-6">Customer profiles</h2>
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        <div className="border border-stone-200 bg-white p-4">
          <SearchableSelect label="Customer" options={opts} value={selected || ""} onChange={setSelected} placeholder="Type name or phone" testid="manager-customer-select" emptyLabel="No customers yet" />
          <p className="mt-3 text-xs text-stone-500">{customers.length} customers</p>
        </div>
        {profile ? (
          <div className="border border-stone-200 bg-white p-6 space-y-4" data-testid="manager-customer-profile">
            <p className="font-serif text-2xl">{profile.customer_name || "Customer"}</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
              <div><p className="text-xs uppercase tracking-[0.2em] text-stone-400">Phone</p><p>{profile.customer_phone}</p></div>
              <div><p className="text-xs uppercase tracking-[0.2em] text-stone-400">Visits</p><p>{profile.visit_count}</p></div>
              <div><p className="text-xs uppercase tracking-[0.2em] text-stone-400">Lifetime spend</p><p>{money(profile.lifetime_spend)}</p></div>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-stone-500 mb-2">Visit history</p>
              <div className="space-y-2 max-h-64 overflow-auto">
                {(profile.visit_history || []).map((v) => <div key={v.id} className="grid grid-cols-1 sm:grid-cols-4 gap-2 border border-stone-100 p-3 text-sm"><span>{v.date}</span><span>{v.service_name}</span><span>{v.stylist_name}</span><span>{money(v.amount_paid)}</span></div>)}
              </div>
            </div>
          </div>
        ) : <p className="text-sm text-stone-500">Select a customer to open a profile.</p>}
      </div>
    </div>
  );
}

function ManagerNoShow({ token }) {
  const [month, setMonth] = useState(format(new Date(), "yyyy-MM"));
  const [data, setData] = useState(null);
  useEffect(() => {
    axios.get(`${API}/manager/no-shows`, { params: { month }, ...managerAuth(token) }).then((r) => setData(r.data));
  }, [month, token]);
  if (!data) return <p className="text-sm text-stone-500">Loading…</p>;
  return (
    <div data-testid="manager-noshow-panel">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div><p className="text-xs uppercase tracking-[0.25em] text-stone-500">Monthly no-show report</p><h2 className="font-serif text-3xl mt-1">Missed appointments</h2></div>
        <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} data-testid="manager-noshow-month-input" className="border border-stone-300 bg-white px-3 py-2 text-sm" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <MetricCard label="No-show rate" value={`${data.no_show_rate.toFixed(1)}%`} testid="manager-noshow-rate" />
        <MetricCard label="No-shows" value={data.total_no_shows} testid="manager-noshow-total" />
        <MetricCard label="Repeat flags" value={data.repeat_customers} testid="manager-noshow-repeat" tone={data.repeat_customers > 0 ? "danger" : "neutral"} />
      </div>
      {data.no_shows.length === 0 ? <p className="text-stone-500" data-testid="manager-noshow-empty">No no-shows recorded for this month.</p> : (
        <div className="space-y-3">
          {data.no_shows.map((b) => (
            <article key={b.id} className={`border p-5 bg-white ${b.repeat_no_show ? "border-rose-500" : "border-stone-200"}`} data-testid={`manager-noshow-row-${b.id}`}>
              <p className="font-serif text-lg">{b.customer_name} <span className="text-sm text-stone-500 font-sans">· {b.customer_phone}</span></p>
              <p className="text-sm text-stone-500">{b.date} · {to12h(b.start_time)} · {b.service?.name} · with {b.stylist?.name}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function ManagerInsights({ token }) {
  return (
    <InsightsDashboard
      authToken={token}
      endpoint="/manager/revenue-insights"
      titleEyebrow="Revenue insights"
      titleMain="Location pulse"
      testidPrefix="manager-insights"
    />
  );
}

function ManagerStylistsView({ token, salonId }) {
  const [stylists, setStylists] = useState([]);
  const [selectedId, setSelectedId] = useState("");
  const [subTab, setSubTab] = useState("today");

  useEffect(() => {
    axios.get(`${API}/stylists`, managerAuth(token))
      .then((r) => {
        const all = Array.isArray(r.data) ? r.data : [];
        // Restrict to stylists belonging to this manager's salon (safety net).
        const scoped = salonId ? all.filter((s) => !s.salon_id || s.salon_id === salonId) : all;
        setStylists(scoped);
      })
      .catch(() => toast.error("Could not load stylists"));
  }, [token, salonId]);

  const stylistOptions = [
    { value: "", label: "All Stylists", search: "all" },
    ...stylists.map((s) => ({
      value: s.id,
      label: `${s.name}${s.title ? ` · ${s.title}` : ""}`,
      search: `${s.name || ""} ${s.title || ""}`,
    })),
  ];
  const selected = stylists.find((s) => s.id === selectedId);
  const SUB_TABS = [
    { k: "today", label: "Today" },
    { k: "customers", label: "Customers" },
    { k: "availability", label: "Weekly availability" },
    { k: "hours", label: "Working hours" },
  ];

  return (
    <div data-testid="manager-stylists-panel">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-6">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-2">Filter</p>
          <div className="w-full sm:w-80">
            <SearchableSelect
              options={stylistOptions}
              value={selectedId}
              onChange={setSelectedId}
              placeholder="All Stylists"
              testid="manager-stylist-filter"
            />
          </div>
        </div>
        {selected && (
          <div className="text-right">
            <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Viewing</p>
            <p className="font-serif text-2xl mt-1" data-testid="manager-stylist-current-name">{selected.name}</p>
            {selected.title && <p className="text-xs text-stone-500">{selected.title}</p>}
          </div>
        )}
      </div>

      {!selected ? (
        <div className="border border-stone-200 bg-white p-8" data-testid="manager-stylists-empty">
          <p className="text-sm text-stone-500 mb-4">
            Select a stylist from the filter above to view their schedule, appointments, availability, and working hours — the same view they see when signed in to their portal.
          </p>
          {stylists.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
              {stylists.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedId(s.id)}
                  data-testid={`manager-stylist-quickpick-${s.id}`}
                  className="text-left border border-stone-200 bg-white p-3 hover:border-stone-900 transition-colors"
                >
                  <p className="font-serif text-base leading-tight">{s.name}</p>
                  <p className="text-[10px] uppercase tracking-[0.18em] text-stone-500 mt-1">{s.title || "Stylist"}</p>
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div>
          <nav className="flex gap-6 border-b border-stone-200 mb-8 overflow-x-auto">
            {SUB_TABS.map((t) => (
              <button
                key={t.k}
                onClick={() => setSubTab(t.k)}
                data-testid={`manager-stylist-subtab-${t.k}`}
                className={`pb-3 text-xs uppercase tracking-[0.2em] border-b-2 -mb-px whitespace-nowrap ${subTab === t.k ? "border-stone-900 text-stone-900" : "border-transparent text-stone-500 hover:text-stone-900"}`}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {/* Reuse StylistPortal views. `key` forces remount when stylist changes so each view fetches fresh data. */}
          {subTab === "today" && <TodayView key={`today-${selected.id}`} stylistId={selected.id} />}
          {subTab === "customers" && <CustomerSearchView key={`cust-${selected.id}`} stylistId={selected.id} />}
          {subTab === "availability" && <AvailabilityView key={`avail-${selected.id}`} stylistId={selected.id} />}
          {subTab === "hours" && <WorkingHoursView key={`hrs-${selected.id}`} stylistId={selected.id} />}
        </div>
      )}
    </div>
  );
}

