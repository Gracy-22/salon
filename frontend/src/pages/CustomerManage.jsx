import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { ArrowLeft, CalendarDays, CheckCircle2, XCircle } from "lucide-react";
import OtpBoxes from "@/components/OtpBoxes";
import { getValidToken, setToken } from "../lib/authStore";
import { sanitizePhoneInput, validatePhone10 } from "../lib/phoneValidation";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const to12h = (time) => {
  const [h, m] = time.split(":").map(Number);
  const suffix = h >= 12 ? "PM" : "AM";
  const hour = h % 12 || 12;
  return `${hour}:${String(m).padStart(2, "0")} ${suffix}`;
};

const todayStr = () => new Date().toISOString().slice(0, 10);

export default function CustomerManage() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));
  // If the user is already logged in as a customer, skip the OTP step and use
  // the cached appointments (populated at login) instead of asking again.
  const storedPhone = typeof window !== "undefined" ? (localStorage.getItem("customer_phone") || "") : "";
  let storedAppointments = [];
  try {
    storedAppointments = JSON.parse((typeof window !== "undefined" ? localStorage.getItem("customer_appointments") : "") || "[]");
  } catch (_e) { storedAppointments = []; }
  const hasStoredSession = !token && Boolean(storedPhone);

  const [otpStep, setOtpStep] = useState(() => {
    if (token) return "token";
    if (hasStoredSession) return "appointments";
    return "phone";
  });
  const [phone, setPhone] = useState(storedPhone);
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState(false);
  const [appointments, setAppointments] = useState(hasStoredSession ? storedAppointments : []);
  const [selectedToken, setSelectedToken] = useState(token || "");
  const [mode, setMode] = useState("reschedule");
  const [newDate, setNewDate] = useState(todayStr());
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [reason, setReason] = useState("schedule_conflict");
  const [actionSuccess, setActionSuccess] = useState(null);
  const [reasonNote, setReasonNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [resendIn, setResendIn] = useState(0);

  useEffect(() => {
    if (resendIn <= 0) return undefined;
    const timer = window.setTimeout(() => setResendIn((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [resendIn]);

  const loadToken = (manageToken = selectedToken) => {
    if (!manageToken) return;
    setLoading(true);
    axios.get(`${API}/customer/manage/${manageToken}`)
      .then((r) => {
        setData(r.data);
        setSelectedToken(manageToken);
        setNewDate(r.data.booking.date);
      })
      .catch(() => toast.error("This manage link is invalid or expired"))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (token) loadToken(token); }, [token]);

  // If we hydrated from a logged-in customer session, refresh the appointment
  // list from the server (so cancellations/reschedules from another device
  // show up here) and preselect the first upcoming appointment.
  useEffect(() => {
    if (!hasStoredSession || token) return;
    const jwt = getValidToken("customer");
    if (jwt) {
      axios
        .get(`${API}/customer/appointments`, { headers: { Authorization: `Bearer ${jwt}` } })
        .then((r) => {
          const fresh = r.data.appointments || [];
          setAppointments(fresh);
          try { localStorage.setItem("customer_appointments", JSON.stringify(fresh)); } catch (_e) { /* storage full */ }
          const first = fresh[0];
          if (first?.manage_token) loadToken(first.manage_token);
        })
        .catch((e) => {
          if (e?.response?.status === 401) setToken("customer", "");
          const first = storedAppointments[0];
          if (first?.manage_token) loadToken(first.manage_token);
        });
    } else {
      const first = storedAppointments[0];
      if (first?.manage_token) loadToken(first.manage_token);
    }
  }, []);

  useEffect(() => {
    if (!data || mode !== "reschedule" || data.booking.status === "cancelled") return;
    setSlots([]);
    setSelectedSlot("");
    axios.get(`${API}/availability`, { params: { stylist_id: data.booking.stylist_id, service_id: data.booking.service_id, date: newDate } })
      .then((r) => setSlots((r.data.slots || []).filter((slot) => slot.available)))
      .catch(() => toast.error("Could not load available slots"));
  }, [data, mode, newDate]);

  const requestOtp = async (e) => {
    e?.preventDefault?.();
    const err = validatePhone10(phone);
    if (err) return toast.error(err);
    setBusy(true);
    try {
      await axios.post(`${API}/customer/manage/request-otp`, { phone });
      const isResend = otpStep === "otp";
      setOtpStep("otp");
      setResendIn(15);
      if (isResend) {
        setOtp("");
        setOtpError(false);
      }
      toast.success(isResend ? "New OTP sent on WhatsApp" : "OTP sent on WhatsApp");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not send OTP");
    } finally {
      setBusy(false);
    }
  };

  const verifyOtp = async (submitted) => {
    if (submitted && typeof submitted.preventDefault === "function") submitted.preventDefault();
    const otpToSend = typeof submitted === "string" ? submitted : otp;
    if (otpToSend.length < 6) return;
    setBusy(true);
    setOtpError(false);
    try {
      const r = await axios.post(`${API}/customer/manage/verify-otp`, { phone, otp: otpToSend });
      setAppointments(r.data.appointments || []);
      setOtpStep("appointments");
      const first = (r.data.appointments || [])[0];
      if (first?.manage_token) loadToken(first.manage_token);
    } catch (e) {
      setOtpError(true);
      setOtp("");
      window.setTimeout(() => setOtpError(false), 600);
      toast.error(e.response?.data?.detail || "Invalid OTP");
    } finally {
      setBusy(false);
    }
  };

  const selectAppointment = (manageToken) => {
    setSelectedToken(manageToken);
    loadToken(manageToken);
  };

  const cancel = async () => {
    if (!window.confirm("Cancel this appointment? This slot will be released immediately.")) return;
    setBusy(true);
    try {
      const r = await axios.post(`${API}/customer/manage/${selectedToken}/cancel`, { reason, reason_note: reasonNote });
      setData(r.data);
      setActionSuccess("cancelled");
      toast.success("Appointment cancelled");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not cancel appointment");
    } finally {
      setBusy(false);
    }
  };

  const reschedule = async () => {
    if (!selectedSlot) return toast.error("Choose a new time slot");
    setBusy(true);
    try {
      const r = await axios.post(`${API}/customer/manage/${selectedToken}/reschedule`, { new_date: newDate, new_start_time: selectedSlot });
      setData(r.data);
      setActionSuccess("rescheduled");
      toast.success("Appointment rescheduled");
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not reschedule appointment");
    } finally {
      setBusy(false);
    }
  };

  const switchAppointment = async () => {
    // "Change service / stylist / salon" — cancel this booking and jump into
    // /book with the current context pre-selected. Cancels FIRST so the slot
    // is released and the user isn't accidentally holding two appointments.
    if (!window.confirm("Cancel this appointment and open the booking flow to pick a different treatment, stylist or salon?")) return;
    setBusy(true);
    try {
      await axios.post(`${API}/customer/manage/${selectedToken}/cancel`, { reason: "customer_reschedule", reason_note: "Switching to a different service/stylist/salon" });
      toast.success("Appointment cancelled — pick your new booking");
      // Redirect with prefill params so /book can drop the user near where they left off.
      const b = data?.booking || {};
      const params = new URLSearchParams();
      if (b.salon_id) params.set("salon", b.salon_id);
      if (b.service_id) params.set("service", b.service_id);
      if (b.stylist_id) params.set("stylist", b.stylist_id);
      window.location.href = `/book${params.toString() ? "?" + params.toString() : ""}`;
    } catch (e) {
      toast.error(e.response?.data?.detail || "Could not cancel this appointment");
      setBusy(false);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-stone-500">Loading your appointment…</div>;

  return (
    <div className="min-h-screen bg-[#FAF9F6] px-6 py-10" data-testid="customer-manage-page">
      <main className="max-w-5xl mx-auto">
        <Link to="/book" className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-stone-500 hover:text-stone-900 mb-8"><ArrowLeft className="h-4 w-4" /> Back to booking</Link>
        {!token && otpStep !== "appointments" && (
          <OtpPanel step={otpStep} phone={phone} setPhone={setPhone} otp={otp} setOtp={setOtp} otpError={otpError} setOtpError={setOtpError} busy={busy} requestOtp={requestOtp} verifyOtp={verifyOtp} resendIn={resendIn} />
        )}
        {!token && otpStep === "appointments" && (
          appointments.length === 0 ? (
            <div className="mb-6 border border-stone-200 bg-white p-8 text-center" data-testid="manage-empty">
              <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-3">No appointments yet</p>
              <p className="font-serif text-2xl mb-4">You don’t have any appointments to manage.</p>
              <Link to="/book" className="inline-block border border-stone-900 bg-stone-900 text-white px-5 py-3 text-xs uppercase tracking-[0.2em] hover:bg-stone-800">Book your first appointment</Link>
            </div>
          ) : (
            <div className="mb-6 border border-stone-200 bg-white p-6" data-testid="manage-appointment-picker">
              <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-3">Select appointment</p>
              <select value={selectedToken} onChange={(e) => selectAppointment(e.target.value)} data-testid="manage-appointment-select" className="w-full border border-stone-300 bg-white px-3 py-3">
                {appointments.map((a) => <option key={a.id} value={a.manage_token}>{a.date} · {to12h(a.start_time)} · {a.service?.name || a.service_name || a.service_id} · {a.status}</option>)}
              </select>
              <p className="mt-2 text-xs text-stone-500" data-testid="manage-appointment-count">{appointments.length} appointments found, including past/cancelled history.</p>
            </div>
          )
        )}
        {data && <ManageCard data={data} mode={mode} setMode={setMode} newDate={newDate} setNewDate={setNewDate} slots={slots} selectedSlot={selectedSlot} setSelectedSlot={setSelectedSlot} reason={reason} setReason={setReason} reasonNote={reasonNote} setReasonNote={setReasonNote} busy={busy} cancel={cancel} reschedule={reschedule} switchAppointment={switchAppointment} actionSuccess={actionSuccess} />}
      </main>
    </div>
  );
}

function OtpPanel({ step, phone, setPhone, otp, setOtp, otpError, setOtpError, busy, requestOtp, verifyOtp, resendIn }) {
  return (
    <div className="bg-white border border-stone-200 p-8 sm:p-10 max-w-xl mx-auto" data-testid="manage-otp-panel">
      <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-3">Manage appointment</p>
      <h1 className="font-serif text-4xl mb-3">Verify your phone</h1>
      <p className="text-stone-500 mb-6">Enter the number used for booking. We’ll send a WhatsApp OTP.</p>
      {step === "phone" ? (
        <form onSubmit={requestOtp}>
          <input
            value={phone}
            onChange={(e) => setPhone(sanitizePhoneInput(e.target.value))}
            placeholder="10-digit mobile"
            inputMode="numeric"
            data-testid="manage-phone-input"
            className={`w-full border px-4 py-3 mb-1 ${validatePhone10(phone, { allowEmpty: true }) ? "border-rose-500" : "border-stone-300"}`}
          />
          {validatePhone10(phone, { allowEmpty: true }) && (
            <p className="mb-3 text-[11px] text-rose-600" data-testid="manage-phone-error">{validatePhone10(phone, { allowEmpty: true })}</p>
          )}
          {!validatePhone10(phone, { allowEmpty: true }) && <div className="mb-3" />}
          <button disabled={busy} data-testid="manage-request-otp" className="border border-stone-900 bg-stone-900 text-white px-5 py-3 text-xs uppercase tracking-[0.2em] disabled:opacity-50">Send OTP</button>
        </form>
      ) : (
        <form onSubmit={verifyOtp}>
          <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-3">Enter 6-digit code</p>
          <div className="mb-5">
            <OtpBoxes
              value={otp}
              onChange={(v) => { setOtp(v); if (otpError) setOtpError(false); }}
              onComplete={(v) => verifyOtp(v)}
              error={otpError}
              disabled={busy}
              testidPrefix="manage-otp"
            />
          </div>
          <div className="flex flex-col sm:flex-row gap-3">
            <button disabled={busy || otp.length < 6} data-testid="manage-verify-otp" className="border border-stone-900 bg-stone-900 text-white px-5 py-3 text-xs uppercase tracking-[0.2em] disabled:opacity-50">Verify OTP</button>
            <button type="button" onClick={requestOtp} disabled={busy || resendIn > 0} data-testid="manage-resend-otp" className="border border-stone-300 px-5 py-3 text-xs uppercase tracking-[0.2em] text-stone-600 hover:border-stone-900 disabled:text-stone-300 disabled:cursor-not-allowed">
              {resendIn > 0 ? `Resend OTP in ${resendIn}s` : "Resend OTP"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function ManageCard({ data, mode, setMode, newDate, setNewDate, slots, selectedSlot, setSelectedSlot, reason, setReason, reasonNote, setReasonNote, busy, cancel, reschedule, switchAppointment, actionSuccess }) {
  const { booking } = data;
  const cancelled = booking.status === "cancelled";
  const done = booking.status === "done";
  return (
    <div className="bg-white border border-stone-200 p-8 sm:p-10" data-testid="manage-card">
      <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-3">Self-serve appointment</p>
      <h1 className="font-serif text-4xl mb-3">Manage your booking</h1>
      <p className="text-stone-500 mb-6" data-testid="manage-policy-notice">{data.policy_notice}</p>
      {data.within_24h && !cancelled && <div className="mb-6 border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800" data-testid="manage-24h-warning">This booking is within 24 hours. You can still continue, but salon policy may apply.</div>}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8" data-testid="manage-booking-summary">
        <Info label="Reference" value={booking.id.slice(0, 8).toUpperCase()} />
        <Info label="Status" value={booking.status} />
        <Info label="Service" value={booking.service?.name || booking.service_name || booking.service_id} />
        <Info label="Stylist" value={booking.stylist?.name || booking.stylist_name || booking.stylist_id} />
        <Info label="Date" value={booking.date} />
        <Info label="Time" value={`${to12h(booking.start_time)} - ${to12h(booking.end_time)}`} />
        <Info label="Name" value={booking.customer_name} />
        <Info label="Phone" value={booking.customer_phone} />
      </div>
      {actionSuccess === "rescheduled" ? <div className="border border-emerald-200 bg-emerald-50 p-5 text-emerald-800" data-testid="manage-rescheduled-state"><CheckCircle2 className="h-5 w-5 inline mr-2" /> Your appointment has been rescheduled. We’ve sent the updated confirmation on WhatsApp.</div> : cancelled || actionSuccess === "cancelled" ? <div className="border border-rose-200 bg-rose-50 p-5 text-rose-800" data-testid="manage-cancelled-state"><XCircle className="h-5 w-5 inline mr-2" /> We’re sorry you can’t make it this time. Your appointment has been cancelled and the slot has been released. We hope to see you again soon.</div> : done ? <div className="border border-stone-200 p-5 text-stone-600" data-testid="manage-done-state"><CheckCircle2 className="h-5 w-5 inline mr-2" /> This appointment is already completed.</div> : <div>
        <div className="inline-flex border border-stone-300 mb-6" data-testid="manage-mode-toggle">
          <button onClick={() => setMode("reschedule")} className={`px-4 py-2 text-xs uppercase tracking-[0.2em] ${mode === "reschedule" ? "bg-stone-900 text-white" : "bg-white"}`}>Reschedule</button>
          <button onClick={() => setMode("cancel")} className={`px-4 py-2 text-xs uppercase tracking-[0.2em] ${mode === "cancel" ? "bg-stone-900 text-white" : "bg-white"}`}>Cancel</button>
        </div>
        {mode === "reschedule" && (
          <section data-testid="manage-reschedule-panel">
            <label className="block mb-4">
              <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">New date</p>
              <input type="date" min={todayStr()} value={newDate} onChange={(e) => setNewDate(e.target.value)} data-testid="manage-new-date" className="border border-stone-300 px-3 py-2" />
            </label>
            <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-3" data-testid="manage-slot-count">
              {slots.length > 0 ? `${slots.length} available slots with ${booking.stylist?.name || booking.stylist_name || "your stylist"}` : "No availability on this date"}
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
              {slots.map((slot) => (
                <button
                  key={slot.start_time}
                  onClick={() => setSelectedSlot(slot.start_time)}
                  data-testid={`manage-slot-${slot.start_time}`}
                  className={`border px-3 py-2 text-sm transition-colors ${selectedSlot === slot.start_time ? "border-stone-900 bg-stone-900 text-white" : "border-stone-300 bg-white hover:border-stone-900"}`}
                >
                  {to12h(slot.start_time)}
                </button>
              ))}
              {slots.length === 0 && (
                <p className="col-span-full text-sm text-stone-500">
                  No available slots on this date. Try another date above, or use the switch below to change stylist / service / salon.
                </p>
              )}
            </div>
            <p className="text-xs text-stone-400 mb-6">Rescheduling keeps the same service, stylist and salon. Need to change any of those? Use the switch below.</p>
            <button onClick={reschedule} disabled={busy || !selectedSlot} data-testid="manage-reschedule-submit" className="inline-flex items-center gap-2 border border-stone-900 bg-stone-900 text-white px-5 py-3 text-xs uppercase tracking-[0.2em] disabled:opacity-50 disabled:cursor-not-allowed">
              <CalendarDays className="h-4 w-4" /> Confirm new slot
            </button>
            <div className="mt-6 pt-6 border-t border-stone-200" data-testid="manage-switch-panel">
              <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-2">Want something different?</p>
              <p className="text-sm text-stone-600 mb-3">Change your treatment, stylist or salon location by booking a fresh appointment. We&apos;ll cancel this one for you first.</p>
              <button
                onClick={switchAppointment}
                disabled={busy}
                data-testid="manage-switch-btn"
                className="inline-flex items-center gap-2 border border-stone-900 bg-white text-stone-900 px-5 py-3 text-xs uppercase tracking-[0.2em] hover:bg-stone-900 hover:text-white transition-colors disabled:opacity-50"
              >
                Cancel & book something else
              </button>
            </div>
          </section>
        )}
        {mode === "cancel" && <section data-testid="manage-cancel-panel"><label className="block mb-3"><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Reason</p><select value={reason} onChange={(e) => setReason(e.target.value)} data-testid="manage-cancel-reason" className="border border-stone-300 px-3 py-2 bg-white w-full sm:w-80">{data.cancellation_reasons.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}</select></label><label className="block mb-5"><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Optional note</p><textarea value={reasonNote} onChange={(e) => setReasonNote(e.target.value)} data-testid="manage-cancel-note" className="border border-stone-300 px-3 py-2 min-h-24 w-full" /></label><button onClick={cancel} disabled={busy} data-testid="manage-cancel-submit" className="border border-rose-700 bg-rose-700 text-white px-5 py-3 text-xs uppercase tracking-[0.2em] disabled:opacity-50">Cancel appointment</button></section>}
      </div>}
    </div>
  );
}

function Info({ label, value }) {
  return <div><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p><p className="font-medium text-stone-800">{value || "—"}</p></div>;
}
