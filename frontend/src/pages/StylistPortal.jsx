import { useEffect, useMemo, useState, useCallback } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { format, addDays, startOfWeek } from "date-fns";
import { toast } from "sonner";
import { LogOut, Clock, CheckCircle2, XCircle, ChevronLeft, ChevronRight, RotateCcw, Coffee, CalendarDays, Phone, ReceiptText, MessageCircle, X } from "lucide-react";
import SearchableSelect from "@/components/SearchableSelect";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const to12h = (t) => {
  if (!t || typeof t !== "string") return t || "";
  const [h, m] = t.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
};

const STATUS_STYLES = {
  upcoming: "bg-stone-100 text-stone-700 border-stone-300",
  in_progress: "bg-amber-100 text-amber-900 border-amber-400",
  done: "bg-emerald-100 text-emerald-900 border-emerald-400",
  no_show: "bg-rose-100 text-rose-900 border-rose-400",
  cancelled: "bg-stone-100 text-stone-400 border-stone-300 line-through",
};
const STATUS_LABEL = { upcoming: "Upcoming", in_progress: "In progress", done: "Done", no_show: "No-show", cancelled: "Cancelled" };
const WEEKDAY_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const money = (value) => `₹${Math.round(Number(value || 0)).toLocaleString("en-IN")}`;
const describeStatus = (status) => status === "break" ? "Break" : status === "leave" ? "Leave" : "Busy";

export default function StylistPortal() {
  const navigate = useNavigate();
  const stylistId = localStorage.getItem("stylist_id");
  const stylistName = localStorage.getItem("stylist_name") || "Stylist";
  const [tab, setTab] = useState("today");

  useEffect(() => {
    if (!stylistId) navigate("/stylist", { replace: true });
  }, [stylistId, navigate]);

  const logout = () => {
    localStorage.removeItem("stylist_id");
    localStorage.removeItem("stylist_name");
    navigate("/stylist", { replace: true });
  };

  if (!stylistId) return null;

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-[#FAF9F6]">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-stone-500">The Gentlemen&apos;s Room</p>
            <h1 className="font-serif text-2xl mt-1" data-testid="portal-stylist-name">{stylistName}</h1>
          </div>
          <button onClick={logout} data-testid="btn-logout" className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-stone-600 hover:text-stone-900">
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6">
        <nav className="flex gap-6 border-b border-stone-200 pt-6">
          {[
            { k: "today", label: "Today" },
            { k: "customers", label: "Customers" },
            { k: "availability", label: "Weekly availability" },
            { k: "hours", label: "Working hours" },
          ].map((t) => (
            <button
              key={t.k}
              onClick={() => setTab(t.k)}
              data-testid={`tab-${t.k}`}
              className={`pb-4 text-sm uppercase tracking-[0.2em] border-b-2 -mb-px ${tab === t.k ? "border-stone-900 text-stone-900" : "border-transparent text-stone-500 hover:text-stone-900"}`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <main className="py-10">
          {tab === "today" && <TodayView stylistId={stylistId} />}
          {tab === "customers" && <CustomerSearchView role="stylist" stylistId={stylistId} />}

          {tab === "availability" && <AvailabilityView stylistId={stylistId} />}
          {tab === "hours" && <WorkingHoursView stylistId={stylistId} />}
        </main>
      </div>
    </div>
  );
}

/* ------------------ Today's schedule ------------------ */
export function TodayView({ stylistId }) {
  const [bookings, setBookings] = useState([]);
  const [blocks, setBlocks] = useState([]);
  const [recurringBlocks, setRecurringBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [profilePhone, setProfilePhone] = useState(null);
  const dateStr = format(selectedDate, "yyyy-MM-dd");

  const load = useCallback(() => {
    setLoading(true);
    axios.get(`${API}/stylist/${stylistId}/schedule`, { params: { date: dateStr } })
      .then((r) => {
        setBookings(r.data.bookings || []);
        setBlocks(r.data.blocks || []);
        setRecurringBlocks(r.data.recurring_blocks || []);
      })
      .finally(() => setLoading(false));
  }, [stylistId, dateStr]);

  useEffect(() => { load(); }, [load]);

  const setStatus = async (booking, status) => {
    try {
      await axios.patch(`${API}/stylist/${stylistId}/bookings/${booking.id}/status`, { status });
      toast.success(status === "no_show" ? "Marked no-show and sent follow-up if available" : `Marked ${STATUS_LABEL[status]}`);
      load();
    } catch {
      toast.error("Could not update status");
    }
  };

  const cancelBooking = async (booking) => {
    if (!window.confirm(`Cancel ${booking.customer_name}'s ${to12h(booking.start_time)} appointment from your stylist schedule?`)) return;
    try {
      await axios.patch(`${API}/stylist/${stylistId}/bookings/${booking.id}/status`, { status: "cancelled" });
      toast.success("Stylist cancellation recorded");
      load();
    } catch {
      toast.error("Could not cancel appointment");
    }
  };

  const enriched = useMemo(() => {
    const today = new Date();
    const isToday = format(today, "yyyy-MM-dd") === dateStr;
    const now = today.getHours() * 60 + today.getMinutes();
    return bookings.map((b) => {
      const s = toMin(b.start_time), e = toMin(b.end_time);
      let displayStatus = b.status;
      if (isToday && displayStatus === "upcoming" && now >= s && now < e) displayStatus = "in_progress";
      return { ...b, displayStatus };
    });
  }, [bookings, dateStr]);

  const next = enriched.find((b) => b.displayStatus === "upcoming" || b.displayStatus === "in_progress");
  const dayItems = useMemo(() => ([
    ...blocks.map((b) => ({ ...b, itemType: "block", title: b.label || describeStatus(b.status), recurring: false })),
    ...recurringBlocks.map((b) => ({ ...b, itemType: "block", title: b.label || describeStatus(b.status), recurring: true })),
    ...enriched.map((b) => ({ ...b, itemType: "booking" })),
  ].sort((a, b) => toMin(a.start_time) - toMin(b.start_time))), [blocks, recurringBlocks, enriched]);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Day view</p>
          <h2 className="font-serif text-3xl sm:text-4xl mt-1" data-testid="day-view-date">{format(selectedDate, "EEEE, d MMMM yyyy")}</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => setSelectedDate(addDays(selectedDate, -1))} data-testid="day-view-prev" className="inline-flex items-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900"><ChevronLeft className="h-3 w-3" /> Prev</button>
          <button onClick={() => setSelectedDate(new Date())} data-testid="day-view-today" className="px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900">Today</button>
          <button onClick={() => setSelectedDate(addDays(selectedDate, 1))} data-testid="day-view-next" className="inline-flex items-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900">Next <ChevronRight className="h-3 w-3" /></button>
          <button onClick={load} data-testid="btn-refresh" className="inline-flex items-center gap-2 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900"><RotateCcw className="h-3 w-3" /> Refresh</button>
        </div>
      </div>

      {next && (
        <div className="border border-stone-900 bg-stone-900 text-stone-50 p-6 mb-8" data-testid="next-appointment">
          <p className="text-xs uppercase tracking-[0.3em] text-stone-300 mb-3">Up next</p>
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <p className="font-serif text-3xl">{to12h(next.start_time)}</p>
            <p className="font-serif text-2xl">{next.customer_name}</p>
            <p className="text-sm text-stone-300">{next.service?.name} · {next.duration_min} min</p>
          </div>
        </div>
      )}

      {loading && <p className="text-sm text-stone-500" data-testid="day-view-loading">Loading…</p>}
      {!loading && dayItems.length === 0 && (
        <p className="text-stone-500" data-testid="no-bookings">No appointments or breaks for this day.</p>
      )}

      <div className="space-y-3" data-testid="today-list">
        {dayItems.map((item) => item.itemType === "block" ? (
          <article key={`${item.recurring ? "rec" : "block"}-${item.id}`} data-testid={`${item.recurring ? "daily-recurring-block" : "daily-block"}-${item.id}`} className="flex flex-col sm:flex-row sm:items-center gap-4 border border-amber-300 bg-amber-50 p-5">
            <div className="flex items-center gap-3 sm:min-w-[180px]">
              <Coffee className="h-4 w-4 text-amber-700" strokeWidth={1.25} />
              <div>
                <p className="font-serif text-xl leading-none">{to12h(item.start_time)}</p>
                <p className="text-xs text-amber-800 mt-1">until {to12h(item.end_time)}</p>
              </div>
            </div>
            <div className="flex-grow">
              <p className="font-serif text-lg leading-tight">{item.title}</p>
              <p className="text-sm text-amber-800">{item.recurring ? "Recurring weekly" : "One-time block"}</p>
            </div>
          </article>
        ) : (
          <article key={item.id} data-testid={`booking-card-${item.id}`} className="flex flex-col xl:flex-row xl:items-center gap-4 xl:gap-6 border border-stone-200 bg-white p-5">
            <div className="flex items-center gap-3 xl:min-w-[150px]">
              <Clock className="h-4 w-4 text-stone-400" strokeWidth={1.25} />
              <div>
                <p className="font-serif text-xl leading-none" data-testid={`daily-booking-time-${item.id}`}>{to12h(item.start_time)}</p>
                <p className="text-xs text-stone-500 mt-1">{item.duration_min} min · ends {to12h(item.end_time)}</p>
              </div>
            </div>
            <div className="flex-grow">
              <p className="font-serif text-lg leading-tight" data-testid={`daily-booking-customer-${item.id}`}>{item.customer_name}</p>
              <p className="text-sm text-stone-500" data-testid={`daily-booking-service-${item.id}`}>{item.service?.name} · {money(item.service?.price || 0)} · Ref {item.id.slice(0, 8).toUpperCase()}</p>
              <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1 text-xs text-stone-500">
                <span data-testid={`daily-booking-phone-${item.id}`} className="inline-flex items-center gap-1"><Phone className="h-3 w-3" /> {item.customer_phone}</span>
                <span data-testid={`daily-booking-whatsapp-${item.id}`} className="inline-flex items-center gap-1"><MessageCircle className="h-3 w-3" /> WhatsApp: {item.whatsapp_status || "pending"}</span>
                {item.notes && <span data-testid={`daily-booking-notes-${item.id}`} className="md:col-span-2 inline-flex items-center gap-1"><ReceiptText className="h-3 w-3" /> {item.notes}</span>}
              </div>
            </div>
            <span data-testid={`status-${item.id}`} className={`inline-flex items-center justify-center px-3 py-1 text-xs uppercase tracking-[0.15em] border ${STATUS_STYLES[item.displayStatus]}`}>
              {STATUS_LABEL[item.displayStatus]}
            </span>
            <div className="flex flex-wrap gap-2 xl:justify-end">
              <button onClick={() => setStatus(item, "done")} disabled={item.status === "done" || item.status === "cancelled"} data-testid={`btn-done-${item.id}`} className="inline-flex items-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-900 text-stone-900 hover:bg-stone-900 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                <CheckCircle2 className="h-3 w-3" /> Done
              </button>
              <button onClick={() => setStatus(item, "no_show")} disabled={item.status === "no_show" || item.status === "cancelled"} data-testid={`btn-noshow-${item.id}`} className="inline-flex items-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 text-stone-700 hover:border-rose-500 hover:text-rose-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
                <XCircle className="h-3 w-3" /> No-show
              </button>
              {item.status !== "cancelled" && item.status !== "done" && (
                <button onClick={() => cancelBooking(item)} data-testid={`btn-cancel-${item.id}`} className="inline-flex items-center justify-center px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 text-stone-700 hover:border-rose-500 hover:text-rose-700 transition-colors">
                  Cancel
                </button>
              )}
              <button onClick={() => setProfilePhone(item.customer_phone)} data-testid={`btn-profile-${item.id}`} className="inline-flex items-center justify-center px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 text-stone-700 hover:border-stone-900 hover:text-stone-900 transition-colors">
                Profile
              </button>
            </div>
          </article>
        ))}
      </div>
      {profilePhone && <CustomerProfileModal phone={profilePhone} stylistId={stylistId} onClose={() => setProfilePhone(null)} />}
    </div>
  );
}

/* ------------------ Working hours editor ------------------ */
export function WorkingHoursView({ stylistId }) {
  const [hours, setHours] = useState({});
  const [loading, setLoading] = useState(true);
  const days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];

  const load = useCallback(() => {
    setLoading(true);
    const ws = format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd");
    axios.get(`${API}/stylist/${stylistId}/availability`, { params: { week_start: ws } })
      .then((r) => setHours(r.data.working_hours || {}))
      .finally(() => setLoading(false));
  }, [stylistId]);

  useEffect(() => { load(); }, [load]);

  const save = async (weekday, payload) => {
    try {
      const { data } = await axios.put(`${API}/stylist/${stylistId}/working-hours`, { weekday, ...payload });
      setHours(data.working_hours);
      toast.success("Hours saved");
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };

  if (loading) return <p className="text-sm text-stone-500">Loading…</p>;

  return (
    <div>
      <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Working hours</p>
      <h2 className="font-serif text-3xl sm:text-4xl mt-1 mb-8">Default weekly schedule</h2>

      <div className="space-y-3 max-w-2xl" data-testid="hours-editor">
        {days.map((label, idx) => {
          const wh = hours[String(idx)];
          const closed = !wh;
          return (
            <div key={label} data-testid={`hours-row-${idx}`} className="flex flex-col sm:flex-row sm:items-center gap-3 border border-stone-200 bg-white p-4">
              <span className="font-serif text-lg w-28">{label}</span>
              <label className="inline-flex items-center gap-2 text-sm text-stone-700">
                <input type="checkbox" checked={!closed} onChange={(e) => save(idx, e.target.checked ? { open: "09:00", close: "21:00", closed: false } : { closed: true })} data-testid={`hours-open-${idx}`} className="h-4 w-4 accent-stone-900" />
                Open
              </label>
              {!closed && (
                <>
                  <input type="time" defaultValue={wh.open} step="900" data-testid={`hours-from-${idx}`} onBlur={(e) => save(idx, { open: e.target.value, close: wh.close, closed: false })} className="border border-stone-300 px-2 py-1 text-sm" />
                  <span className="text-stone-400">to</span>
                  <input type="time" defaultValue={wh.close} step="900" data-testid={`hours-to-${idx}`} onBlur={(e) => save(idx, { open: wh.open, close: e.target.value, closed: false })} className="border border-stone-300 px-2 py-1 text-sm" />
                </>
              )}
              {closed && <span className="text-sm text-stone-400 italic">Closed</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------ Weekly availability ------------------ */
export function AvailabilityView({ stylistId }) {
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [data, setData] = useState({ working_hours: {}, blocks: [], bookings: [] });
  const [loading, setLoading] = useState(true);
  const [blockForm, setBlockForm] = useState({ mode: "one-time", date: format(new Date(), "yyyy-MM-dd"), start_time: "13:00", end_time: "14:00", label: "Lunch break", customLabel: "", weekdays: [0,1,2,3,4] });
  const [selectedItem, setSelectedItem] = useState(null);

  const weekStartStr = format(weekStart, "yyyy-MM-dd");
  const load = useCallback(() => {
    setLoading(true);
    axios.get(`${API}/stylist/${stylistId}/availability`, { params: { week_start: weekStartStr } })
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [stylistId, weekStartStr]);

  useEffect(() => { load(); }, [load]);

  const addBlock = async (date, start, end, status = "break") => {
    try {
      await axios.put(`${API}/stylist/${stylistId}/blocks`, { date, start_time: start, end_time: end, status });
      toast.success(`Marked ${describeStatus(status)}`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not save");
    }
  };

  const addBreak = async () => {
    const resolvedLabel = (blockForm.label === "Other" ? (blockForm.customLabel || "").trim() : blockForm.label) || "Break";
    try {
      if (blockForm.mode === "recurring") {
        await axios.put(`${API}/stylist/${stylistId}/recurring-blocks`, {
          weekdays: blockForm.weekdays,
          start_time: blockForm.start_time,
          end_time: blockForm.end_time,
          status: "break",
          label: resolvedLabel,
        });
      } else {
        await axios.put(`${API}/stylist/${stylistId}/blocks`, {
          date: blockForm.date,
          start_time: blockForm.start_time,
          end_time: blockForm.end_time,
          status: "break",
          label: resolvedLabel,
        });
      }
      toast.success(`${resolvedLabel} added${blockForm.mode === "recurring" ? " (weekly)" : ""}`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not add break");
    }
  };

  const removeBlock = async (id) => {
    try {
      await axios.delete(`${API}/stylist/${stylistId}/blocks/${id}`);
      load();
    } catch {
      toast.error("Could not remove");
    }
  };

  const removeRecurringBlock = async (id) => {
    try {
      await axios.delete(`${API}/stylist/${stylistId}/recurring-blocks/${id}`);
      load();
    } catch {
      toast.error("Could not remove recurring break");
    }
  };

  // Build 30-minute time grid 09:00..21:00
  const timeSlots = useMemo(() => {
    const arr = [];
    for (let m = 9 * 60; m < 21 * 60; m += 30) arr.push(m);
    return arr;
  }, []);
  const weekDates = useMemo(() => DAY_NAMES.map((_, i) => addDays(weekStart, i)), [weekStart]);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Weekly availability</p>
          <h2 className="font-serif text-3xl mt-1" data-testid="week-label">
            {format(weekStart, "d MMM")} – {format(addDays(weekStart, 6), "d MMM yyyy")}
          </h2>
        </div>
        <div className="flex gap-2">
          <button data-testid="btn-prev-week" onClick={() => setWeekStart(addDays(weekStart, -7))} className="inline-flex items-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900">
            <ChevronLeft className="h-3 w-3" /> Prev
          </button>
          <button data-testid="btn-this-week" onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))} className="px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900">
            This week
          </button>
          <button data-testid="btn-next-week" onClick={() => setWeekStart(addDays(weekStart, 7))} className="inline-flex items-center gap-1 px-3 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900">
            Next <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      <Legend />
      <BreakManager
        weekDates={weekDates}
        form={blockForm}
        setForm={setBlockForm}
        onAdd={addBreak}
        recurringBlocks={data.recurring_blocks || []}
        onRemoveRecurring={removeRecurringBlock}
      />

      {loading && <p className="text-sm text-stone-500 mt-6">Loading…</p>}
      {!loading && (
        <div className="overflow-x-auto mt-6" data-testid="availability-grid">
          <div className="min-w-[1040px]">
            <div className="grid grid-cols-[72px_repeat(7,_1fr)] gap-px bg-stone-200 relative">
              <div className="bg-[#FAF9F6]" />
              {weekDates.map((date, i) => {
                const dateStr = format(date, "yyyy-MM-dd");
                return (
                  <div key={DAY_NAMES[i]} className="bg-[#FAF9F6] p-2 text-center">
                    <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{DAY_NAMES[i]}</p>
                    <p className="font-serif text-lg">{format(date, "d")}</p>
                    <p className="text-[10px] text-stone-400" data-testid={`day-header-${dateStr}`}>{dateStr}</p>
                  </div>
                );
              })}
              <div className="col-span-8 grid grid-cols-[72px_repeat(7,_1fr)] gap-px bg-stone-200 relative">
                {timeSlots.map((m) => <TimeLabel key={m} minute={m} />)}
                {weekDates.map((date, dayIndex) => (
                  <DayColumn
                    key={format(date, "yyyy-MM-dd")}
                    date={date}
                    dayIndex={dayIndex}
                    data={data}
                    onAvailableClick={(start, end) => addBlock(format(date, "yyyy-MM-dd"), start, end, "busy")}
                    onUnblock={removeBlock}
                    onSelectItem={setSelectedItem}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {selectedItem && <BookingDetailModal item={selectedItem} onClose={() => setSelectedItem(null)} />}
    </div>
  );
}

function Legend() {
  const items = [
    { c: "bg-emerald-50 border-emerald-300", l: "Available" },
    { c: "bg-stone-900 border-stone-900", l: "Booked" },
    { c: "bg-amber-50 border-amber-400", l: "Busy" },
    { c: "bg-yellow-50 border-yellow-400", l: "Break / lunch" },
    { c: "bg-rose-50 border-rose-400", l: "On leave" },
    { c: "bg-stone-50 border-stone-200 opacity-50", l: "Outside hours" },
  ];
  return (
    <div className="flex flex-wrap gap-4 text-xs">
      {items.map((it) => (
        <span key={it.l} className="inline-flex items-center gap-2">
          <span className={`inline-block h-3 w-3 border ${it.c}`} /> {it.l}
        </span>
      ))}
    </div>
  );
}

function toMin(t) { const [h, m] = t.split(":").map(Number); return h * 60 + m; }
function minToT(m) { return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`; }

function BreakManager({ weekDates, form, setForm, onAdd, recurringBlocks, onRemoveRecurring }) {
  const toggleWeekday = (idx) => {
    const next = form.weekdays.includes(idx) ? form.weekdays.filter((d) => d !== idx) : [...form.weekdays, idx].sort();
    setForm({ ...form, weekdays: next });
  };
  return (
    <section className="mt-6 border border-stone-200 bg-white p-5" data-testid="break-manager">
      <div className="flex items-center gap-2 mb-4">
        <Coffee className="h-4 w-4 text-stone-500" />
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Lunch & break hours</p>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[130px_1fr_auto_auto_170px_auto] gap-3 items-end">
        <label className="text-xs uppercase tracking-[0.16em] text-stone-500">
          Type
          <select value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })} data-testid="break-mode-select" className="mt-2 w-full border border-stone-300 bg-white px-2 py-2 text-sm">
            <option value="one-time">One-time</option>
            <option value="recurring">Recurring weekly</option>
          </select>
        </label>
        {form.mode === "one-time" ? (
          <label className="text-xs uppercase tracking-[0.16em] text-stone-500">
            Date
            <select value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} data-testid="break-date-select" className="mt-2 w-full border border-stone-300 bg-white px-2 py-2 text-sm">
              {weekDates.map((date) => <option key={format(date, "yyyy-MM-dd")} value={format(date, "yyyy-MM-dd")}>{format(date, "EEE, d MMM")}</option>)}
            </select>
          </label>
        ) : (
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-stone-500 mb-2">Days</p>
            <div className="flex flex-wrap gap-2">
              {DAY_NAMES.map((d, idx) => (
                <button type="button" key={d} onClick={() => toggleWeekday(idx)} data-testid={`break-weekday-${idx}`} className={`px-2 py-2 text-xs border ${form.weekdays.includes(idx) ? "border-stone-900 bg-stone-900 text-white" : "border-stone-300 bg-white text-stone-600"}`}>{d}</button>
              ))}
            </div>
          </div>
        )}
        <label className="text-xs uppercase tracking-[0.16em] text-stone-500">
          From
          <input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} data-testid="break-start-input" className="mt-2 w-full border border-stone-300 px-2 py-2 text-sm" />
        </label>
        <label className="text-xs uppercase tracking-[0.16em] text-stone-500">
          To
          <input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} data-testid="break-end-input" className="mt-2 w-full border border-stone-300 px-2 py-2 text-sm" />
        </label>
        <label className="text-xs uppercase tracking-[0.16em] text-stone-500">
          Tag
          <select
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            data-testid="break-label-select"
            className="mt-2 w-full border border-stone-300 bg-white px-2 py-2 text-sm"
          >
            <option value="Lunch break">Lunch break</option>
            <option value="Tea break">Tea break</option>
            <option value="Personal break">Personal break</option>
            <option value="Prayer break">Prayer break</option>
            <option value="Meeting">Meeting</option>
            <option value="Other">Other…</option>
          </select>
          {form.label === "Other" && (
            <input
              type="text"
              value={form.customLabel || ""}
              onChange={(e) => setForm({ ...form, customLabel: e.target.value })}
              data-testid="break-custom-label-input"
              placeholder="e.g. Errand"
              className="mt-2 w-full border border-stone-300 px-2 py-2 text-sm"
            />
          )}
        </label>
        <button type="button" onClick={onAdd} data-testid="break-add-button" className="px-4 py-3 bg-stone-900 text-white text-xs uppercase tracking-[0.15em] hover:bg-stone-800">Add break</button>
      </div>
      {recurringBlocks.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2" data-testid="recurring-break-list">
          {recurringBlocks.map((b) => (
            <span key={b.id} data-testid={`recurring-break-${b.id}`} className="inline-flex items-center gap-2 border border-yellow-400 bg-yellow-50 px-3 py-2 text-xs text-yellow-900">
              {b.label || "Break"}: {b.weekdays.map((d) => DAY_NAMES[d]).join(", ")} · {to12h(b.start_time)}–{to12h(b.end_time)}
              <button type="button" onClick={() => onRemoveRecurring(b.id)} data-testid={`remove-recurring-break-${b.id}`} className="text-yellow-900 hover:text-rose-700"><X className="h-3 w-3" /></button>
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

function TimeLabel({ minute }) {
  return <div className="col-start-1 bg-[#FAF9F6] py-2 px-2 text-right text-[11px] text-stone-500 h-14 border-b border-stone-100">{to12h(minToT(minute))}</div>;
}

function DayColumn({ date, dayIndex, data, onAvailableClick, onUnblock, onSelectItem }) {
  const dateStr = format(date, "yyyy-MM-dd");
  const weekday = (date.getDay() + 6) % 7;
  const wh = data.working_hours?.[String(weekday)];
  const dayStart = 9 * 60;
  const dayEnd = 21 * 60;
  const gridRows = (dayEnd - dayStart) / 30;
  const items = [
    ...(data.bookings || []).filter((b) => b.date === dateStr).map((b) => ({ ...b, itemType: "booking" })),
    ...(data.blocks || []).filter((b) => b.date === dateStr).map((b) => ({ ...b, itemType: "block", recurring: false })),
    ...(data.recurring_blocks || []).filter((b) => (b.weekdays || []).includes(weekday)).map((b) => ({ ...b, itemType: "block", recurring: true })),
  ];
  return (
    <div className="relative bg-white" style={{ gridColumn: dayIndex + 2, gridRow: `1 / span ${gridRows}` }} data-testid={`weekly-day-column-${dateStr}`}>
      {Array.from({ length: gridRows }).map((_, idx) => {
        const start = dayStart + idx * 30;
        const end = start + 30;
        const insideWH = wh && start >= toMin(wh.open) && end <= toMin(wh.close);
        const hasItem = items.some((it) => !(toMin(it.end_time) <= start || toMin(it.start_time) >= end));
        return (
          <button
            key={idx}
            type="button"
            disabled={!insideWH || hasItem}
            onClick={() => onAvailableClick(minToT(start), minToT(end))}
            data-testid={`weekly-slot-${dateStr}-${minToT(start)}-${insideWH ? hasItem ? "occupied" : "available" : "outside"}`}
            className={`block h-14 w-full border-b border-stone-100 text-left ${insideWH ? hasItem ? "bg-transparent" : "bg-emerald-50/40 hover:bg-emerald-100" : "bg-stone-50 opacity-70"}`}
            title={insideWH && !hasItem ? "Click to mark busy" : ""}
          />
        );
      })}
      {items.map((item) => <CalendarBlock key={`${item.itemType}-${item.id}`} item={item} dayStart={dayStart} onUnblock={onUnblock} onSelectItem={onSelectItem} />)}
    </div>
  );
}

function CalendarBlock({ item, dayStart, onUnblock, onSelectItem }) {
  const top = ((toMin(item.start_time) - dayStart) / 30) * 56;
  const height = Math.max(28, ((toMin(item.end_time) - toMin(item.start_time)) / 30) * 56 - 4);
  const isBooking = item.itemType === "booking";
  const blockStyle = isBooking ? "bg-stone-900 text-white border-stone-900" : item.status === "leave" ? "bg-rose-50 text-rose-900 border-rose-400" : item.status === "break" ? "bg-yellow-50 text-yellow-900 border-yellow-400" : "bg-amber-50 text-amber-900 border-amber-400";
  return (
    <button
      type="button"
      onClick={() => isBooking ? onSelectItem(item) : !item.recurring && onUnblock(item.id)}
      disabled={!isBooking && item.recurring}
      data-testid={`${isBooking ? "weekly-booking-block" : item.recurring ? "weekly-recurring-block" : "weekly-block"}-${item.id}`}
      className={`absolute left-1 right-1 z-10 overflow-hidden border p-2 text-left text-xs shadow-sm ${blockStyle}`}
      style={{ top, height }}
      title={isBooking ? "Click for booking details" : item.recurring ? "Recurring break" : "Click to clear"}
    >
      <span className="block font-serif text-sm truncate">{isBooking ? item.customer_name : item.label || describeStatus(item.status)}</span>
      <span className="block text-[10px] opacity-80 truncate">{to12h(item.start_time)}–{to12h(item.end_time)} {isBooking ? `· ${item.service?.name || "Service"}` : item.recurring ? "· weekly" : ""}</span>
    </button>
  );
}

function BookingDetailModal({ item, onClose }) {
  return (
    <div className="fixed inset-0 z-50 bg-stone-950/30 flex items-center justify-center p-4" data-testid="booking-detail-modal">
      <div className="bg-white border border-stone-200 max-w-lg w-full p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Booking details</p>
            <h3 className="font-serif text-3xl mt-1" data-testid="modal-booking-customer">{item.customer_name}</h3>
          </div>
          <button type="button" onClick={onClose} data-testid="booking-detail-close" className="border border-stone-300 p-2 hover:border-stone-900"><X className="h-4 w-4" /></button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <Info label="Time" value={`${to12h(item.start_time)} – ${to12h(item.end_time)}`} testid="modal-booking-time" />
          <Info label="Duration" value={`${item.duration_min} min`} testid="modal-booking-duration" />
          <Info label="Service" value={item.service?.name || "—"} testid="modal-booking-service" />
          <Info label="Price" value={money(item.service?.price || 0)} testid="modal-booking-price" />
          <Info label="Phone" value={item.customer_phone} testid="modal-booking-phone" />
          <Info label="Status" value={STATUS_LABEL[item.status] || item.status} testid="modal-booking-status" />
          <Info label="Reference" value={item.id.slice(0, 8).toUpperCase()} testid="modal-booking-reference" />
          <Info label="WhatsApp" value={item.whatsapp_status || "pending"} testid="modal-booking-whatsapp" />
          <div className="sm:col-span-2">
            <Info label="Notes" value={item.notes || "—"} testid="modal-booking-notes" />
          </div>
        </div>
      </div>
    </div>
  );
}

function CustomerProfileModal({ phone, stylistId, onClose }) {
  return (
    <div className="fixed inset-0 z-50 bg-stone-950/30 flex items-center justify-center p-4" data-testid="customer-profile-modal">
      <div className="bg-white border border-stone-200 max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Customer profile</p>
            <h3 className="font-serif text-3xl mt-1">History & preferences</h3>
          </div>
          <button type="button" onClick={onClose} data-testid="customer-profile-close" className="border border-stone-300 p-2 hover:border-stone-900"><X className="h-4 w-4" /></button>
        </div>
        <CustomerProfilePanel endpointBase={`${API}/stylist/${stylistId}/customers`} phone={phone} />
      </div>
    </div>
  );
}

export function CustomerSearchView({ stylistId }) {
  const [customers, setCustomers] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState(null);
  const customerOptions = customers.map((c) => ({ value: c.customer_phone, label: `${c.customer_name || "Customer"} · ${c.customer_phone}`, search: `${c.customer_name || ""} ${c.customer_phone || ""}` }));
  const loadCustomers = useCallback(() => {
    axios.get(`${API}/stylist/${stylistId}/customers/search`).then((r) => {
      const rows = r.data.customers || [];
      setCustomers(rows);
      setSelectedPhone((current) => current || rows[0]?.customer_phone || null);
    });
  }, [stylistId]);
  useEffect(() => { loadCustomers(); }, [loadCustomers]);
  const selectedCustomer = customers.find((c) => c.customer_phone === selectedPhone);
  return (
    <section data-testid="stylist-customer-search">
      <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Customer history</p>
      <h2 className="font-serif text-3xl sm:text-4xl mt-1 mb-6">Find a client</h2>
      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        <div className="border border-stone-200 bg-white p-4">
          <SearchableSelect label="Customer" options={customerOptions} value={selectedPhone || ""} onChange={setSelectedPhone} placeholder="Type name or phone" testid="stylist-customer-select" emptyLabel="No customers found" />
          <p className="mt-3 text-xs text-stone-500" data-testid="stylist-customer-count">{customers.length} customers</p>
          {selectedCustomer && <p className="mt-4 font-serif text-xl" data-testid="stylist-selected-customer">{selectedCustomer.customer_name || "Customer"}</p>}
        </div>
        {selectedPhone ? <CustomerProfilePanel endpointBase={`${API}/stylist/${stylistId}/customers`} phone={selectedPhone} onSaved={loadCustomers} /> : <p className="text-sm text-stone-500">Select a customer to view history and preferences.</p>}
      </div>
    </section>
  );
}

function CustomerProfilePanel({ endpointBase, phone, onSaved }) {
  const [profile, setProfile] = useState(null);
  const [stylists, setStylists] = useState([]);
  const [form, setForm] = useState({});
  const loadProfile = useCallback(() => {
    axios.get(`${endpointBase}/${phone}`).then((r) => {
      setProfile(r.data);
      setForm({
        customer_phone: r.data.customer_phone,
        customer_name: r.data.customer_name || "",
        birthday: r.data.birthday || "",
        hair_type: r.data.hair_type || "",
        product_allergies: r.data.product_allergies || "",
        preferences: r.data.preferences || "",
        stylist_notes: r.data.stylist_notes || "",
        preferred_stylist_id: r.data.preferred_stylist_manual ? r.data.preferred_stylist_id : "",
      });
    });
  }, [endpointBase, phone]);
  useEffect(() => { loadProfile(); axios.get(`${API}/stylists`).then((r) => setStylists(r.data || [])); }, [loadProfile]);
  const save = async () => {
    await axios.patch(`${endpointBase}/${phone}`, form);
    toast.success("Customer profile saved");
    loadProfile();
    onSaved?.();
  };
  if (!profile) return <p className="text-sm text-stone-500">Loading profile…</p>;
  return (
    <div data-testid="customer-profile-panel" className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <Info label="Phone" value={profile.customer_phone} testid="profile-phone" />
        <Info label="Visits" value={profile.visit_count} testid="profile-visits" />
        <Info label="Lifetime spend" value={money(profile.lifetime_spend)} testid="profile-spend" />
        <Info label="Preferred stylist" value={`${profile.preferred_stylist_name || "—"}${profile.preferred_stylist_manual ? " · manual" : profile.preferred_stylist_name ? " · auto" : ""}`} testid="profile-preferred" />
      </div>
      <div className="border border-stone-200 p-4">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-3">Preferences & notes</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ProfileInput label="Name" value={form.customer_name} onChange={(v) => setForm({ ...form, customer_name: v })} testid="profile-name-input" />
          <ProfileInput label="Birthday" type="date" value={form.birthday} onChange={(v) => setForm({ ...form, birthday: v })} testid="profile-birthday-input" />
          <ProfileInput label="Hair type" value={form.hair_type} onChange={(v) => setForm({ ...form, hair_type: v })} testid="profile-hair-input" />
          <ProfileInput label="Product allergies" value={form.product_allergies} onChange={(v) => setForm({ ...form, product_allergies: v })} testid="profile-allergy-input" />
          <div><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Preferred stylist override</p><select value={form.preferred_stylist_id} onChange={(e) => setForm({ ...form, preferred_stylist_id: e.target.value })} data-testid="profile-preferred-select" className="w-full border border-stone-300 px-3 py-2 bg-white"><option value="">Auto ({profile.preferred_stylist_name || "none"})</option>{stylists.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
          <ProfileInput label="Preferences" value={form.preferences} onChange={(v) => setForm({ ...form, preferences: v })} testid="profile-preferences-input" textarea />
          <ProfileInput label="Stylist notes" value={form.stylist_notes} onChange={(v) => setForm({ ...form, stylist_notes: v })} testid="profile-notes-input" textarea />
        </div>
        <button onClick={save} data-testid="profile-save-button" className="mt-4 border border-stone-900 bg-stone-900 text-white px-4 py-2 text-xs uppercase tracking-[0.2em]">Save profile</button>
      </div>
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-3">Visit history</p>
        <div className="space-y-2 max-h-72 overflow-auto" data-testid="profile-visit-history">
          {(profile.visit_history || []).map((v) => <div key={v.id} className="grid grid-cols-1 sm:grid-cols-4 gap-2 border border-stone-100 p-3 text-sm"><span>{v.date}</span><span>{v.service_name}</span><span>{v.stylist_name}</span><span>{money(v.amount_paid)}</span></div>)}
        </div>
      </div>
    </div>
  );
}

function ProfileInput({ label, value, onChange, testid, type = "text", textarea = false }) {
  return <label className="block"><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p>{textarea ? <textarea value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={testid} className="w-full border border-stone-300 px-3 py-2 min-h-20" /> : <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={testid} className="w-full border border-stone-300 px-3 py-2" />}</label>;
}

function Info({ label, value, testid }) {
  return <div><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p><p className="font-medium text-stone-800" data-testid={testid}>{value}</p></div>;
}

