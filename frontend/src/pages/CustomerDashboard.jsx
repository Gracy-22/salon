import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { CalendarDays, Clock, Scissors, UserRound } from "lucide-react";
import { getValidToken, setToken } from "../lib/authStore";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const money = (value) => `₹${Math.round(Number(value || 0)).toLocaleString("en-IN")}`;

/**
 * Human-readable "time until" for an appointment. Falls back to null when the
 * appointment is in the past (history) or the input is malformed.
 */
function timeUntil(dateStr, timeStr) {
  if (!dateStr) return null;
  const [y, m, d] = dateStr.split("-").map(Number);
  const [hh = 0, mm = 0] = (timeStr || "00:00").split(":").map(Number);
  if (!y || !m || !d) return null;
  const target = new Date(y, m - 1, d, hh, mm, 0, 0);
  const now = new Date();
  const diffMs = target.getTime() - now.getTime();
  if (diffMs <= 0) return null;
  const minutes = Math.round(diffMs / 60000);
  const hours = Math.round(minutes / 60);
  // Compare calendar days so "tomorrow" doesn't get overshadowed by an
  // "in 23 hours" phrasing when the appointment is on the next day.
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfTarget = new Date(y, m - 1, d).getTime();
  const days = Math.round((startOfTarget - startOfToday) / 86400000);
  // Same-day: use hour/minute phrasing
  if (days === 0) {
    if (minutes < 60) return minutes <= 5 ? "starting soon" : `in ${minutes} min`;
    return hours === 1 ? "in 1 hour" : `in ${hours} hours`;
  }
  if (days === 1) return "tomorrow";
  if (days < 7) return `in ${days} days`;
  if (days < 14) return "in 1 week";
  const weeks = Math.round(days / 7);
  if (weeks < 5) return `in ${weeks} weeks`;
  const months = Math.round(days / 30);
  return months === 1 ? "in 1 month" : `in ${months} months`;
}

export default function CustomerDashboard() {
  const [phone] = useState(() => localStorage.getItem("customer_phone") || "");
  const [appointments, setAppointments] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("customer_appointments") || "[]");
    } catch (_e) {
      return [];
    }
  });
  const navigate = useNavigate();

  useEffect(() => {
    if (!phone) {
      navigate("/login");
      return;
    }
    // Refresh appointments from the server using the customer JWT so the
    // dashboard reflects reschedules/cancellations made from another device
    // or since the last login. Falls back silently to the cached snapshot
    // if the token is missing/expired (login flow handles the re-auth).
    const token = getValidToken("customer");
    if (!token) return;
    axios
      .get(`${API}/customer/appointments`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        const fresh = r.data.appointments || [];
        setAppointments(fresh);
        try { localStorage.setItem("customer_appointments", JSON.stringify(fresh)); } catch (_e) { /* storage full */ }
      })
      .catch((e) => {
        if (e?.response?.status === 401) {
          setToken("customer", "");
        }
        // else: keep the cached list — we still render offline-friendly data
      });
  }, [phone, navigate]);

  const upcoming = appointments.filter((a) => a.status !== "cancelled" && a.status !== "done");
  const history = appointments.filter((a) => a.status === "cancelled" || a.status === "done");

  return (
    <div className="min-h-screen bg-[#FAF9F6] px-6 py-10" data-testid="customer-dashboard">
      <main className="max-w-5xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-stone-500">Customer dashboard</p>
            <h1 className="font-serif text-4xl mt-2">Your appointments</h1>
            <p className="text-stone-500 mt-2">Logged in as {phone}</p>
          </div>
          <div className="flex gap-3">
            <Link to="/book" data-testid="customer-book-new" className="inline-flex items-center gap-2 bg-stone-900 text-white px-5 py-3 text-xs uppercase tracking-[0.2em]"><CalendarDays className="h-4 w-4" /> Book new</Link>
            <Link to="/manage" data-testid="customer-manage-link" className="inline-flex items-center gap-2 border border-stone-300 bg-white px-5 py-3 text-xs uppercase tracking-[0.2em]">Manage</Link>
          </div>
        </div>
        <section className="mb-8">
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-3">Upcoming</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {upcoming.map((a) => <AppointmentCard key={a.id} appointment={a} />)}
            {upcoming.length === 0 && <p className="text-sm text-stone-500">No upcoming appointments.</p>}
          </div>
        </section>
        <section>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-3">History</p>
          <div className="space-y-3">
            {history.map((a) => <AppointmentCard key={a.id} appointment={a} compact />)}
            {history.length === 0 && <p className="text-sm text-stone-500">No past visits yet.</p>}
          </div>
        </section>
      </main>
    </div>
  );
}

function AppointmentCard({ appointment, compact = false }) {
  const until = !compact ? timeUntil(appointment.date, appointment.start_time) : null;
  return (
    <article className="border border-stone-200 bg-white p-5" data-testid={`customer-appointment-${appointment.id}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-serif text-2xl">{appointment.service?.name || appointment.service_name || appointment.service_id}</p>
          <p className="text-sm text-stone-500 mt-1"><UserRound className="h-3 w-3 inline mr-1" /> {appointment.stylist?.name || appointment.stylist_name || appointment.stylist_id}</p>
          <p className="text-sm text-stone-500"><Clock className="h-3 w-3 inline mr-1" /> {appointment.date} · {appointment.start_time}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="text-xs uppercase tracking-[0.18em] text-stone-500">{appointment.status}</span>
          {until && (
            <span
              data-testid={`customer-appointment-until-${appointment.id}`}
              className="text-[11px] uppercase tracking-[0.18em] px-2 py-1 bg-stone-900 text-white"
            >
              {until}
            </span>
          )}
        </div>
      </div>
      {!compact && <Link to={`/manage/${appointment.manage_token}`} className="mt-4 inline-flex items-center gap-2 border border-stone-900 px-4 py-2 text-xs uppercase tracking-[0.2em] hover:bg-stone-900 hover:text-white"><Scissors className="h-4 w-4" /> Reschedule / cancel</Link>}
    </article>
  );
}
