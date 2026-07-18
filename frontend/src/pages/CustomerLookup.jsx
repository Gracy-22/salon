import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { format, addDays } from "date-fns";
import { toast } from "sonner";
import { ArrowLeft, Search, Calendar as CalendarIcon, Clock } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Calendar } from "@/components/ui/calendar";
import { sanitizePhoneInput, validatePhone10 } from "../lib/phoneValidation";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const to12h = (t) => {
  if (!t || typeof t !== "string") return t || "";
  const [h, m] = t.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
};

export default function CustomerLookup() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [bookings, setBookings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [rescheduling, setRescheduling] = useState(null); // {booking}
  const [newDate, setNewDate] = useState(null);
  const [newSlots, setNewSlots] = useState([]);
  const [newSlot, setNewSlot] = useState(null);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const search = async () => {
    const err = validatePhone10(phone);
    if (err) return toast.error(err);
    setLoading(true);
    setBookings(null);
    try {
      const { data } = await axios.post(`${API}/lookup`, { phone, code: code || null });
      setBookings(data.bookings);
    } catch { toast.error("Lookup failed"); }
    finally { setLoading(false); }
  };

  const openReschedule = (b) => {
    setRescheduling({ booking: b });
    setNewDate(null); setNewSlots([]); setNewSlot(null);
  };

  const cancelBooking = async (b) => {
    if (!window.confirm(`Cancel your ${b.service?.name} on ${b.date} at ${to12h(b.start_time)}?`)) return;
    try {
      await axios.post(`${API}/customer/cancel`, { booking_id: b.id, phone });
      toast.success("Booking cancelled");
      search();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Cancel failed");
    }
  };

  const loadSlots = async (b, d) => {
    setSlotsLoading(true);
    try {
      const { data } = await axios.get(`${API}/availability`, { params: { stylist_id: b.stylist_id, service_id: b.service_id, date: format(d, "yyyy-MM-dd") } });
      setNewSlots(data.slots);
    } finally { setSlotsLoading(false); }
  };

  const confirmReschedule = async () => {
    if (!newDate || !newSlot) return;
    setSubmitting(true);
    try {
      await axios.post(`${API}/customer/reschedule`, {
        booking_id: rescheduling.booking.id,
        phone,
        new_date: format(newDate, "yyyy-MM-dd"),
        new_start_time: newSlot.start_time,
      });
      toast.success("Rescheduled");
      setRescheduling(null);
      search();
    } catch (e) { toast.error(e?.response?.data?.detail || "Could not reschedule"); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200">
        <div className="max-w-3xl mx-auto px-6 py-6 flex items-center justify-between">
          <button onClick={() => navigate("/")} className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-stone-500 hover:text-stone-900"><ArrowLeft className="h-3 w-3" /> Home</button>
          <p className="font-serif text-xl">Find my booking</p>
          <span className="w-12" />
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_140px_auto] gap-3 items-end mb-8">
          <div>
            <Label className="text-xs uppercase tracking-[0.2em] text-stone-500">Phone</Label>
            <Input
              value={phone}
              onChange={(e) => setPhone(sanitizePhoneInput(e.target.value))}
              placeholder="10-digit mobile"
              inputMode="numeric"
              data-testid="lookup-phone"
              className={`mt-2 rounded-none bg-white h-12 focus-visible:ring-stone-900 ${validatePhone10(phone, { allowEmpty: true }) ? "border-rose-500" : "border-stone-300"}`}
            />
            {validatePhone10(phone, { allowEmpty: true }) && (
              <p className="mt-1 text-[11px] text-rose-600" data-testid="lookup-phone-error">{validatePhone10(phone, { allowEmpty: true })}</p>
            )}
          </div>
          <div>
            <Label className="text-xs uppercase tracking-[0.2em] text-stone-500">Ref (last 4)</Label>
            <Input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} placeholder="A1B2" data-testid="lookup-code" className="mt-2 rounded-none border-stone-300 bg-white h-12 uppercase focus-visible:ring-stone-900" />
          </div>
          <button onClick={search} disabled={!phone || loading} data-testid="btn-lookup" className={`h-12 px-6 inline-flex items-center gap-2 uppercase tracking-[0.15em] text-sm ${!phone || loading ? "bg-stone-200 text-stone-400" : "bg-stone-900 text-white hover:bg-stone-800"}`}>
            <Search className="h-4 w-4" /> Find
          </button>
        </div>

        {loading && <p className="text-sm text-stone-500">Searching…</p>}
        {bookings && bookings.length === 0 && <p className="text-stone-500" data-testid="lookup-empty">No bookings found for that phone.</p>}

        <div className="space-y-4" data-testid="lookup-results">
          {bookings && bookings.map((b) => (
            <article key={b.id} data-testid={`lookup-booking-${b.id}`} className="border border-stone-200 bg-white p-6 flex flex-col md:flex-row md:items-center gap-6">
              <div className="flex-grow">
                <p className="text-xs uppercase tracking-[0.2em] text-stone-400">Ref {b.id.slice(0,8).toUpperCase()}</p>
                <p className="font-serif text-xl mt-1">{b.service?.name}</p>
                <p className="text-sm text-stone-500">with {b.stylist?.name}</p>
                <div className="flex flex-wrap gap-4 mt-3 text-sm text-stone-700">
                  <span className="inline-flex items-center gap-1"><CalendarIcon className="h-3 w-3" /> {b.date}</span>
                  <span className="inline-flex items-center gap-1"><Clock className="h-3 w-3" /> {to12h(b.start_time)} — {to12h(b.end_time)}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => openReschedule(b)} disabled={b.status === "cancelled" || b.status === "done"} data-testid={`btn-reschedule-${b.id}`} className="px-4 py-2 text-xs uppercase tracking-[0.15em] border border-stone-900 hover:bg-stone-900 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed">Reschedule</button>
                <button onClick={() => cancelBooking(b)} disabled={b.status === "cancelled" || b.status === "done"} data-testid={`btn-cancel-${b.id}`} className="px-4 py-2 text-xs uppercase tracking-[0.15em] border border-stone-300 text-stone-700 hover:border-rose-500 hover:text-rose-700 disabled:opacity-40 disabled:cursor-not-allowed">Cancel</button>
              </div>
            </article>
          ))}
        </div>

        {rescheduling && (
          <div className="fixed inset-0 bg-stone-900/40 flex items-center justify-center px-4 z-50" data-testid="reschedule-modal">
            <div className="bg-white border border-stone-300 max-w-2xl w-full p-8 max-h-[90vh] overflow-y-auto">
              <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-2">Reschedule</p>
              <h3 className="font-serif text-2xl mb-6">{rescheduling.booking.service?.name} · {rescheduling.booking.stylist?.name}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                <div className="border border-stone-200 p-3">
                  <Calendar mode="single" selected={newDate} onSelect={(d) => { setNewDate(d); setNewSlot(null); if (d) loadSlots(rescheduling.booking, d); }} disabled={(d) => d < new Date(new Date().setHours(0,0,0,0))} className="rounded-none" />
                </div>
                <div>
                  {!newDate && <p className="text-sm text-stone-500">Pick a new date.</p>}
                  {newDate && slotsLoading && <p className="text-sm text-stone-500">Loading…</p>}
                  {newDate && !slotsLoading && (
                    <div className="grid grid-cols-3 gap-2 max-h-[300px] overflow-y-auto" data-testid="reschedule-slots">
                      {newSlots.filter((s) => s.available).map((s) => {
                        const sel = newSlot?.start_time === s.start_time;
                        return (
                          <button key={s.start_time} type="button" onClick={() => setNewSlot(s)} data-testid={`reschedule-slot-${s.start_time}`}
                            className={`py-2 text-sm border transition-all ${sel ? "bg-stone-900 text-white border-stone-900" : "bg-white border-stone-200 hover:border-stone-900 hover:-translate-y-0.5"}`}>{to12h(s.start_time)}</button>
                        );
                      })}
                      {newSlots.filter((s) => s.available).length === 0 && (
                        <p className="text-sm text-stone-500 col-span-3">No times available on this day.</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8">
                <button onClick={() => setRescheduling(null)} className="px-5 py-3 text-sm uppercase tracking-[0.15em] border border-stone-300 hover:border-stone-900">Cancel</button>
                <button onClick={confirmReschedule} disabled={!newSlot || submitting} data-testid="btn-confirm-reschedule" className={`px-5 py-3 text-sm uppercase tracking-[0.15em] ${!newSlot || submitting ? "bg-stone-200 text-stone-400" : "bg-stone-900 text-white hover:bg-stone-800"}`}>{submitting ? "Saving…" : "Confirm new time"}</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
