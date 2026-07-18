import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { toast } from "sonner";
import { format } from "date-fns";
import {
  Scissors,
  Wind,
  ScissorsLineDashed,
  Leaf,
  Droplets,
  Sparkles,
  Sun,
  Flower2,
  Hand,
  Check,
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Clock,
  User,
  Phone as PhoneIcon,
  ArrowLeft,
  MapPin,
  Search,
} from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// 24h "HH:MM" -> "h:mm AM/PM"
const to12h = (t) => {
  if (!t || typeof t !== "string") return t || "";
  const [h, m] = t.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
};

const toMin = (t) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };

const groupSlots = (slots) => {
  const groups = { Morning: [], Afternoon: [], Evening: [] };
  for (const s of slots) {
    const m = toMin(s.start_time);
    if (m < 12 * 60) groups.Morning.push(s);
    else if (m < 17 * 60) groups.Afternoon.push(s);
    else groups.Evening.push(s);
  }
  return groups;
};

const ICONS = {
  Scissors,
  Wind,
  ScissorsLineDashed,
  Leaf,
  Droplets,
  Sparkles,
  Sun,
  Flower2,
  Hand,
};

const STEPS_STYLIST_FIRST = ["Location", "Service", "Stylist", "Date & Time"];
const STEPS_SLOT_FIRST = ["Location", "Service", "Date & Time", "Stylist"];
const LAST_STEP = 3;

export default function BookingFlow() {
  const [step, setStep] = useState(0);
  const [mode, setMode] = useState("stylist_first"); // or "slot_first"
  const [services, setServices] = useState([]);
  const [salons, setSalons] = useState([]);
  const [stylists, setStylists] = useState([]);

  const [service, setService] = useState(null);
  const [salon, setSalon] = useState(null);
  const [stylist, setStylist] = useState(null);
  const [date, setDate] = useState(() => new Date());
  const [slot, setSlot] = useState(null);
  const [slots, setSlots] = useState([]);
  const [slotsLoading, setSlotsLoading] = useState(false);

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [whatsappOptin, setWhatsappOptin] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [confirmedBooking, setConfirmedBooking] = useState(null);
  const [customerReady, setCustomerReady] = useState(false);
  const [profileLoading, setProfileLoading] = useState(true);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [birthday, setBirthday] = useState("");
  const customerPhone = localStorage.getItem("customer_phone") || "";



  useEffect(() => {
    if (!customerPhone) {
      setProfileLoading(false);
      return;
    }
    setPhone(customerPhone);
    axios.get(`${API}/customer/profile/${customerPhone}`).then((r) => {
      setName(r.data.customer_name || "");
      setBirthday(r.data.birthday || "");
      setNeedsProfile(!(r.data.customer_name || "").trim() || !r.data.birthday);
      setCustomerReady(Boolean((r.data.customer_name || "").trim() && r.data.birthday));
    }).catch(() => setNeedsProfile(true)).finally(() => setProfileLoading(false));
  }, [customerPhone]);

  // Load salons (list of branches) on mount — Location is now step 0.
  useEffect(() => {
    axios
      .get(`${API}/salons`)
      .then((r) => setSalons(r.data.salons || []))
      .catch(() => toast.error("Could not load salons"));
  }, []);

  // Prefill from URL query (?salon=… &service=… &stylist=…).
  // ?salon runs first so that services can be filtered by the chosen branch.
  useEffect(() => {
    if (!salons.length || salon) return;
    try {
      const params = new URLSearchParams(window.location.search);
      const preSalonId = params.get("salon");
      if (preSalonId) {
        const preSalon = salons.find((s) => s.id === preSalonId);
        if (preSalon) { setSalon(preSalon); setStep((prev) => (prev < 1 ? 1 : prev)); }
      }
    } catch (_e) { /* ignore */ }
  }, [salons, salon]);

  // Load services filtered by the selected salon; only offered services show up.
  useEffect(() => {
    if (!salon) { setServices([]); return; }
    axios
      .get(`${API}/services`, { params: { salon_id: salon.id } })
      .then((r) => {
        setServices(r.data);
        // If a service was requested via URL and it's offered here, preselect it
        // and advance to the Stylist / Date step.
        try {
          const params = new URLSearchParams(window.location.search);
          const sId = params.get("service");
          if (sId) {
            const preService = (r.data || []).find((s) => s.id === sId);
            if (preService) { setService(preService); setStep((prev) => (prev < 2 ? 2 : prev)); }
          }
        } catch (_e) { /* ignore */ }
      })
      .catch(() => toast.error("Could not load services"));
  }, [salon]);

  // If ?stylist=... in URL, jump to Date/Time step once stylists load.
  useEffect(() => {
    if (!stylists.length || stylist) return;
    try {
      const params = new URLSearchParams(window.location.search);
      const preStylistId = params.get("stylist");
      if (preStylistId) {
        const preStylist = stylists.find((s) => s.id === preStylistId);
        if (preStylist) { setStylist(preStylist); setStep((prev) => (prev < 3 ? 3 : prev)); }
      }
    } catch (_e) { /* ignore */ }
  }, [stylists, stylist]);

  // Load stylists — either all stylists at salon offering service, or filtered by slot in slot_first mode
  useEffect(() => {
    if (!service || !salon) return;
    if (mode === "slot_first") {
      if (!slot) { setStylists([]); return; }
      const dateStr = format(date, "yyyy-MM-dd");
      axios
        .get(`${API}/availability/by-slot`, { params: { salon_id: salon.id, service_id: service.id, date: dateStr, start_time: slot.start_time } })
        .then((r) => setStylists(r.data.stylists || []))
        .catch(() => toast.error("Could not load stylists"));
    } else {
      axios
        .get(`${API}/stylists`, { params: { service_id: service.id, salon_id: salon.id } })
        .then((r) => setStylists(r.data))
        .catch(() => toast.error("Could not load stylists"));
    }
  }, [service, salon, mode, slot, date]);

  // stylist_first: Load per-stylist availability when date+stylist+service selected
  useEffect(() => {
    if (mode !== "stylist_first" || !service || !stylist || !date) return;
    const dateStr = format(date, "yyyy-MM-dd");
    setSlotsLoading(true);
    setSlot(null);
    axios
      .get(`${API}/availability`, {
        params: { stylist_id: stylist.id, service_id: service.id, date: dateStr },
      })
      .then((r) => setSlots(r.data.slots))
      .catch(() => toast.error("Could not load availability"))
      .finally(() => setSlotsLoading(false));
  }, [mode, service, stylist, date]);

  // slot_first: Load salon-wide slot union when date+service+salon selected
  useEffect(() => {
    if (mode !== "slot_first" || !service || !salon || !date) return;
    const dateStr = format(date, "yyyy-MM-dd");
    setSlotsLoading(true);
    setSlot(null);
    axios
      .get(`${API}/availability/salon-slots`, {
        params: { salon_id: salon.id, service_id: service.id, date: dateStr },
      })
      .then((r) => setSlots(r.data.slots))
      .catch(() => toast.error("Could not load availability"))
      .finally(() => setSlotsLoading(false));
  }, [mode, service, salon, date]);

  const canProceed = useMemo(() => {
    if (step === 0) return !!salon;
    if (step === 1) return !!service;
    if (mode === "slot_first") {
      if (step === 2) return !!date && !!slot;
      if (step === 3) return !!stylist;
    } else {
      if (step === 2) return !!stylist;
      if (step === 3) return !!date && !!slot;
    }
    return false;
  }, [step, mode, service, salon, stylist, date, slot]);

  const goBack = () => setStep((s) => Math.max(0, s - 1));
  const goNext = () => setStep((s) => Math.min(LAST_STEP, s + 1));

  const saveProfile = async () => {
    if (!customerPhone) return;
    if (name.trim().length < 2 || !birthday) return toast.error("Please add your name and birth date");
    await axios.patch(`${API}/customer/profile/${customerPhone}`, { customer_name: name.trim(), birthday });
    setCustomerReady(true);
    setNeedsProfile(false);
    toast.success("Profile saved");
  };

  const logoutCustomer = () => {
    localStorage.removeItem("customer_phone");
    window.location.href = "/login";
  };

  const handleSubmit = async () => {
    if (!customerReady) {
      setNeedsProfile(true);
      return toast.error("Complete your profile before booking");
    }
    setSubmitting(true);
    try {
      const dateStr = format(date, "yyyy-MM-dd");
      const { data } = await axios.post(`${API}/bookings`, {
        service_id: service.id,
        stylist_id: stylist.id,
        date: dateStr,
        start_time: slot.start_time,
        customer_name: name,
        customer_phone: phone,
        notes,
        whatsapp_optin: whatsappOptin,
      });
      setConfirmedBooking(data);
      toast.success("Booking confirmed");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Booking failed");
    } finally {
      setSubmitting(false);
    }
  };

  const resetAll = () => {
    setStep(0);
    setService(null);
    setSalon(null);
    setStylist(null);
    setDate(new Date());
    setSlot(null);
    setSlots([]);
    setName("");
    setPhone("");
    setNotes("");
    setWhatsappOptin(true);
    setConfirmedBooking(null);
  };

  if (confirmedBooking) {
    return <ConfirmationScreen data={confirmedBooking} onReset={resetAll} />;
  }

  if (profileLoading) {
    return <div className="min-h-screen flex items-center justify-center text-stone-500">Loading your profile…</div>;
  }

  if (!customerPhone) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6 py-16 bg-[#FAF9F6]" data-testid="booking-login-required">
        <div className="max-w-md border border-stone-200 bg-white p-8 text-center">
          <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-3">Login required</p>
          <h1 className="font-serif text-4xl mb-4">Sign in to book</h1>
          <p className="text-stone-500 mb-6">Please verify your phone first so we can use your saved profile for booking.</p>
          <button onClick={() => window.location.href = "/login"} className="bg-stone-900 text-white px-6 py-3 text-xs uppercase tracking-[0.2em]">Login with OTP</button>
        </div>
      </div>
    );
  }

  if (needsProfile) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6 py-16 bg-[#FAF9F6]" data-testid="booking-profile-required">
        <div className="max-w-lg w-full border border-stone-200 bg-white p-8">
          <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-3">First visit details</p>
          <h1 className="font-serif text-4xl mb-4">Tell us about you</h1>
          <p className="text-stone-500 mb-6">We’ll save this once and use it for future bookings.</p>
          <label className="block mb-4"><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Full name</p><input value={name} onChange={(e) => setName(e.target.value)} data-testid="booking-profile-name" className="w-full border border-stone-300 px-4 py-3" /></label>
          <label className="block mb-6"><p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Birth date</p><input type="date" value={birthday} onChange={(e) => setBirthday(e.target.value)} data-testid="booking-profile-birthday" className="w-full border border-stone-300 px-4 py-3" /></label>
          <button onClick={saveProfile} data-testid="booking-profile-save" className="w-full bg-stone-900 text-white px-6 py-3 text-xs uppercase tracking-[0.2em]">Continue to booking</button>
          <button onClick={logoutCustomer} className="mt-3 w-full text-xs uppercase tracking-[0.2em] text-stone-500">Logout</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header customerPhone={customerPhone} onLogout={logoutCustomer} salon={salon} />

      <main className={`max-w-5xl mx-auto px-6 py-10 md:py-16 ${step === 1 ? "pb-28 md:pb-28" : ""}`}>
        {step >= 2 && (
          <ModeToggle
            mode={mode}
            onChange={(m) => { setMode(m); setStylist(null); setSlot(null); }}
          />
        )}
        <Stepper currentStep={step} mode={mode} />

        <section className="step-enter" key={`${mode}-${step}`}>
          {step === 0 && (
            <LocationStep
              salons={salons}
              selected={salon}
              onSelect={(s) => {
                // Changing branch invalidates every downstream selection so the
                // customer is always looking at services actually offered here.
                if (salon && salon.id !== s.id) {
                  setService(null);
                }
                setSalon(s);
                setStylist(null);
                setSlot(null);
              }}
            />
          )}
          {step === 1 && (
            <ServiceStep
              services={services}
              selected={service}
              onSelect={(s) => {
                setService(s);
                // reset downstream
                setStylist(null);
                setSlot(null);
                setDate(new Date());
              }}
            />
          )}
          {step === 2 && mode === "stylist_first" && (
            <StylistStep
              stylists={stylists}
              selected={stylist}
              onSelect={(s) => {
                setStylist(s);
                setSlot(null);
                setDate(new Date());
              }}
            />
          )}
          {step === 2 && mode === "slot_first" && (
            <DateTimeStep
              date={date}
              onDateChange={setDate}
              slots={slots}
              slot={slot}
              onSlotSelect={setSlot}
              loading={slotsLoading}
              service={service}
              stylist={null}
              salon={salon}
              slotFirst={true}
            />
          )}
          {step === 3 && mode === "stylist_first" && (
            <DateTimeStep
              date={date}
              onDateChange={setDate}
              slots={slots}
              slot={slot}
              onSlotSelect={setSlot}
              loading={slotsLoading}
              service={service}
              stylist={stylist}
              salon={salon}
              slotFirst={false}
            />
          )}
          {step === 3 && mode === "slot_first" && (
            <StylistStep
              stylists={stylists}
              selected={stylist}
              onSelect={setStylist}
              slotFirstContext={{ date, slot, salon }}
            />
          )}
        </section>

        <Footer
          step={step}
          canProceed={canProceed}
          onBack={goBack}
          onNext={step === LAST_STEP ? handleSubmit : goNext}
          submitting={submitting}
          isLast={step === LAST_STEP}
          sticky={step === 1}
        />
      </main>
    </div>
  );
}

/* ============================================================ */
/* Header                                                       */
/* ============================================================ */
function Header({ customerPhone, onLogout, salon }) {
  const salonLabel = salon
    ? `${salon.name}${salon.timezone ? ` · ${salon.timezone}` : ""}`
    : null;
  return (
    <header
      className="border-b border-stone-200 bg-[#FAF9F6]"
      data-testid="site-header"
    >
      <div className="max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <h1 className="font-serif text-3xl tracking-tight" data-testid="brand-name">
            The Gentlemen&apos;s Room
          </h1>
          <span className="hidden sm:inline text-xs uppercase tracking-[0.3em] text-stone-500">
            Hair · Skin · Wellness
          </span>
        </div>
        <div className="flex items-center gap-6">
          <a href="/manage" data-testid="link-lookup" className="hidden sm:inline text-xs uppercase tracking-[0.2em] text-stone-500 hover:text-stone-900">
            My Booking
          </a>
          {customerPhone && (
            <button onClick={onLogout} data-testid="booking-logout-button" className="text-xs uppercase tracking-[0.2em] text-stone-500 hover:text-stone-900">
              Logout
            </button>
          )}
          {salonLabel && (
            <span className="hidden md:inline text-xs uppercase tracking-[0.2em] text-stone-500" data-testid="header-salon-label">
              {salonLabel}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}

/* ============================================================ */
/* Mode Toggle (segmented, sits above the Stepper)              */
/* ============================================================ */
function ModeToggle({ mode, onChange }) {
  const OPTIONS = [
    { value: "stylist_first", label: "Pick stylist first", hint: "See open slots for a chosen stylist." },
    { value: "slot_first", label: "Pick slot first", hint: "Pick a time, see which stylists are free." },
  ];
  return (
    <div className="mb-6" data-testid="booking-mode-toggle">
      <p className="text-[10px] uppercase tracking-[0.3em] text-stone-400 mb-2">Booking preference</p>
      <div className="inline-flex flex-col sm:flex-row w-full sm:w-auto border border-stone-300 bg-white">
        {OPTIONS.map((opt) => {
          const active = mode === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange(opt.value)}
              data-testid={`mode-${opt.value.replace("_", "-")}`}
              className={`px-4 py-2.5 text-left sm:text-center transition-colors border-b sm:border-b-0 sm:border-r border-stone-200 last:border-b-0 sm:last:border-r-0 ${
                active ? "bg-stone-900 text-white" : "text-stone-700 hover:bg-stone-50"
              }`}
              aria-pressed={active}
            >
              <p className="text-xs uppercase tracking-[0.18em]">{opt.label}</p>
              <p className={`text-[11px] mt-0.5 ${active ? "text-stone-300" : "text-stone-500"}`}>{opt.hint}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}


/* ============================================================ */
/* Stepper                                                      */
/* ============================================================ */
function Stepper({ currentStep, mode }) {
  const STEPS = mode === "slot_first" ? STEPS_SLOT_FIRST : STEPS_STYLIST_FIRST;
  return (
    <div className="mb-12 border-b border-stone-200 pb-6" data-testid="stepper">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">
          Step {currentStep + 1} of {STEPS.length}
        </p>
        <ol className="flex flex-wrap items-center gap-x-6 gap-y-2">
          {STEPS.map((label, i) => {
            const active = i === currentStep;
            const done = i < currentStep;
            return (
              <li key={label} className="flex items-center gap-2" data-testid={`stepper-item-${i}`}>
                <span
                  className={`h-6 w-6 inline-flex items-center justify-center text-xs border ${
                    active
                      ? "border-stone-900 bg-stone-900 text-white"
                      : done
                      ? "border-stone-900 bg-white text-stone-900"
                      : "border-stone-300 bg-white text-stone-400"
                  }`}
                >
                  {done ? <Check className="h-3 w-3" /> : i + 1}
                </span>
                <span
                  className={`text-sm font-light tracking-wide ${
                    active ? "text-stone-900" : "text-stone-500"
                  }`}
                >
                  {label}
                </span>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}

/* ============================================================ */
/* Service Step                                                 */
/* ============================================================ */
function ServiceStep({ services, selected, onSelect }) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const filtered = q
    ? services.filter((s) =>
        [s.name, s.category, s.description].some((f) => (f || "").toLowerCase().includes(q))
      )
    : services;
  return (
    <div>
      <h2 className="font-serif text-3xl sm:text-4xl mb-2">Choose your service</h2>
      <p className="text-stone-500 mb-6 max-w-xl">
        Every ritual is timed and crafted by our team. Select what calls you today.
      </p>

      <div className="relative mb-8 max-w-md" data-testid="service-search-wrapper">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400" strokeWidth={1.5} />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search services (name, category, keyword)"
          data-testid="service-search-input"
          className="w-full pl-10 pr-10 py-3 border border-stone-200 bg-white text-sm placeholder:text-stone-400 focus:outline-none focus:border-stone-900 transition-colors"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery("")}
            data-testid="service-search-clear"
            aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-xs uppercase tracking-[0.18em] text-stone-500 hover:text-stone-900"
          >
            Clear
          </button>
        )}
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-stone-500 border border-stone-200 bg-white p-6" data-testid="services-empty">
          No services match &quot;{query}&quot;. Try a different keyword.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="services-grid">
          {filtered.map((s) => {
            const Icon = ICONS[s.icon] || Sparkles;
            const isSel = selected?.id === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => onSelect(s)}
                data-testid={`service-card-${s.id}`}
                className={`text-left flex flex-col p-7 border bg-white transition-all duration-300 ${
                  isSel
                    ? "border-stone-900 ring-1 ring-stone-900"
                    : "border-stone-200 hover:border-stone-900"
                }`}
              >
                <div className="flex items-start justify-between mb-6">
                  <Icon className="h-6 w-6 text-stone-700" strokeWidth={1.25} />
                  <span className="text-xs uppercase tracking-[0.2em] text-stone-400">
                    {s.category}
                  </span>
                </div>
                <h3 className="font-serif text-xl mb-2">{s.name}</h3>
                <p className="text-sm text-stone-500 mb-6 flex-grow">{s.description}</p>
                <div className="flex items-center justify-between text-sm font-light">
                  <span className="text-stone-500">{s.duration_min} min</span>
                  <span className="text-stone-900">₹{s.price}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}


/* ============================================================ */
/* Location Step                                                */
/* ============================================================ */
function LocationStep({ salons, selected, onSelect }) {
  return (
    <div data-testid="location-step">
      <h2 className="font-serif text-3xl sm:text-4xl mb-2">Choose your location</h2>
      <p className="text-stone-500 mb-8 max-w-xl">
        Pick the salon that works best for you. Each location has its own team and hours.
      </p>

      {salons.length === 0 ? (
        <p className="text-stone-500" data-testid="locations-empty">No locations offering this treatment yet.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="locations-grid">
          {salons.map((s) => {
            const isSel = selected?.id === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => onSelect(s)}
                data-testid={`location-card-${s.id}`}
                className={`text-left border p-4 transition-colors ${isSel ? "border-stone-900 ring-1 ring-stone-900" : "border-stone-200 hover:border-stone-900"}`}
              >
                <div className="flex items-start gap-3">
                  <MapPin className="h-5 w-5 mt-0.5 text-stone-500" />
                  <div className="min-w-0">
                    <p className="font-serif text-xl">{s.name}</p>
                    <p className="text-xs text-stone-500 mt-1">{[s.city, s.address].filter(Boolean).join(" · ") || "—"}</p>
                    {s.phone && <p className="text-xs text-stone-500 mt-0.5">{s.phone}</p>}
                    <p className="text-[10px] uppercase tracking-[0.2em] text-stone-400 mt-2">{s.timezone}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ============================================================ */
/* Stylist Step                                                 */
/* ============================================================ */
function StylistStep({ stylists, selected, onSelect, slotFirstContext }) {
  const contextLabel = slotFirstContext?.slot && slotFirstContext?.date
    ? `Stylists free at ${slotFirstContext.slot.start_time} on ${format(slotFirstContext.date, "d MMM")}${slotFirstContext.salon ? ` at ${slotFirstContext.salon.name}` : ""}`
    : null;
  return (
    <div>
      <h2 className="font-serif text-3xl sm:text-4xl mb-2">Select your stylist</h2>
      <p className="text-stone-500 mb-10 max-w-xl" data-testid="stylist-step-subtitle">
        {contextLabel || "Each of our artists brings a distinct hand. Choose the one who feels right."}
      </p>

      {stylists.length === 0 && (
        <p className="text-stone-500 border border-stone-200 bg-stone-50 p-6" data-testid="stylists-empty">
          {slotFirstContext ? "No stylists free at that slot. Go back and pick another time." : "No stylists available for this selection."}
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-10" data-testid="stylists-grid">
        {stylists.map((s) => {
          const isSel = selected?.id === s.id;
          return (
            <button
              key={s.id}
              type="button"
              onClick={() => onSelect(s)}
              data-testid={`stylist-card-${s.id}`}
              className={`text-left group flex flex-col gap-5 ${
                isSel ? "" : ""
              }`}
            >
              <div
                className={`overflow-hidden border ${
                  isSel ? "border-stone-900 ring-1 ring-stone-900" : "border-stone-200"
                }`}
              >
                {s.photo ? (
                  <img
                    src={s.photo}
                    alt={s.name}
                    className={`aspect-[3/4] object-cover w-full transition-all duration-700 ease-out ${
                      isSel ? "" : "grayscale group-hover:grayscale-0"
                    }`}
                  />
                ) : (
                  <div className="aspect-[3/4] w-full bg-stone-100 flex items-center justify-center" data-testid={`stylist-card-initials-${s.id}`}>
                    <span className="font-serif text-5xl text-stone-400">
                      {(s.name || "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase()}
                    </span>
                  </div>
                )}
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="font-serif text-xl">{s.name}</h3>
                  {isSel && (
                    <span className="inline-flex items-center gap-1 text-xs uppercase tracking-[0.2em] text-stone-900">
                      <Check className="h-3 w-3" /> Selected
                    </span>
                  )}
                </div>
                <p className="text-xs uppercase tracking-[0.2em] text-stone-500 mt-1">
                  {s.title}
                </p>
                <p className="text-sm text-stone-600 mt-3 leading-relaxed">{s.bio}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ============================================================ */
/* Date & Time Step                                             */
/* ============================================================ */
function DateTimeStep({ date, onDateChange, slots, slot, onSlotSelect, loading, service, stylist, salon, slotFirst }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const windowDays = Math.max(1, Math.min(365, Number(salon?.booking_window_days) || 30));
  const latestBookableDate = new Date(today);
  latestBookableDate.setDate(latestBookableDate.getDate() + windowDays);
  today.setHours(0, 0, 0, 0);

  return (
    <div>
      <h2 className="font-serif text-3xl sm:text-4xl mb-2">Pick a date & time</h2>
      <p className="text-stone-500 mb-10 max-w-xl" data-testid="datetime-subtitle">
        {slotFirst
          ? `${service?.name} at ${salon?.name || "salon"} · ${service?.duration_min} minutes · showing slots when at least one stylist is free.`
          : `${service?.name} with ${stylist?.name} · ${service?.duration_min} minutes.`}
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div className="border border-stone-200 bg-white p-4" data-testid="date-picker">
          <Calendar
            mode="single"
            selected={date}
            onSelect={onDateChange}
            disabled={(d) => d < today || d > latestBookableDate}
            fromDate={today}
            toDate={latestBookableDate}
            className="rounded-none"
            components={{ DayContent: BookingCalendarDayContent }}
          />
          <p className="text-[11px] text-stone-400 mt-3" data-testid="booking-window-hint">
            {salon?.name || "This salon"} accepts bookings up to {windowDays} days ahead
            {" · "}
            latest date: {format(latestBookableDate, "d MMM yyyy")}.
          </p>
        </div>

        <div data-testid="slots-panel">
          {(() => {
            // Filter out slots whose start time has already passed when viewing today.
            // TODO: change cutoff to (now + 10 min) once travel-time buffer is enabled.
            const nowRef = new Date();
            const isToday = date && format(date, "yyyy-MM-dd") === format(nowRef, "yyyy-MM-dd");
            const cutoffMinutes = isToday ? nowRef.getHours() * 60 + nowRef.getMinutes() : -1;
            const displaySlots = isToday
              ? slots.filter((s) => {
                  const [h, m] = s.start_time.split(":").map(Number);
                  return h * 60 + m > cutoffMinutes;
                })
              : slots;
            return (
              <>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-serif text-xl">
                    {date ? format(date, "EEEE, d MMMM") : "Select a date"}
                  </h3>
                  {date && (
                    <span className="text-xs uppercase tracking-[0.2em] text-stone-500" data-testid="slots-count">
                      {displaySlots.filter((s) => s.available).length} available
                    </span>
                  )}
                </div>

                {!date && (
                  <p className="text-sm text-stone-500" data-testid="slots-empty">
                    Choose a date to view available times.
                  </p>
                )}

                {date && loading && (
                  <p className="text-sm text-stone-500" data-testid="slots-loading">Loading…</p>
                )}

                {date && !loading && displaySlots.length > 0 && (() => {
                  const grouped = groupSlots(displaySlots);
                  const totalFree = displaySlots.filter((s) => s.available).length;
                  if (totalFree === 0) {
                    return (
                      <div className="border border-stone-200 bg-white p-6 text-sm text-stone-500" data-testid="slots-none">
                        {isToday
                          ? "No more openings today — please try tomorrow."
                          : "Fully booked — please try another day."}
                      </div>
                    );
                  }
                  return (
                    <div className="space-y-6 max-h-[460px] overflow-y-auto pr-2 slots-grid" data-testid="slots-grid">
                      {Object.entries(grouped).map(([label, list]) => {
                        const freeList = list.filter((s) => s.available);
                        if (freeList.length === 0) return null;
                        return (
                          <div key={label} data-testid={`slot-group-${label.toLowerCase()}`}>
                            <div className="flex items-center gap-3 mb-3">
                              <p className="text-xs uppercase tracking-[0.25em] text-stone-500">{label}</p>
                              <span className="flex-grow h-px bg-stone-200" />
                              <span className="text-[10px] text-stone-400">{freeList.length} open</span>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                              {freeList.map((s) => {
                                const isSel = slot?.start_time === s.start_time;
                                return (
                                  <button
                                    key={s.start_time}
                                    type="button"
                                    onClick={() => onSlotSelect(s)}
                                    data-testid={`slot-${s.start_time}`}
                                    className={`py-3 px-3 text-center text-sm font-light border transition-all duration-200 ${
                                      isSel
                                        ? "bg-stone-900 text-white border-stone-900 shadow-sm"
                                        : "bg-white text-stone-900 border-stone-200 hover:border-stone-900 hover:-translate-y-0.5"
                                    }`}
                                  >
                                    {to12h(s.start_time)}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}

                {date && !loading && displaySlots.length === 0 && slots.length > 0 && (
                  <div className="border border-stone-200 bg-white p-6 text-sm text-stone-500" data-testid="slots-none-today">
                    No more openings today — please try tomorrow.
                  </div>
                )}
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

function BookingCalendarDayContent({ date: dayDate }) {
  const dayId = dayDate ? format(dayDate, "yyyy-MM-dd") : "unknown";
  return (
    <span
      data-testid={`date-day-${dayId}`}
    >
      {dayDate?.getDate?.()}
    </span>
  );
}

/* ============================================================ */
/* Details Step                                                 */
/* ============================================================ */
function DetailsStep({ name, phone, notes, whatsappOptin, setName, setPhone, setNotes, setWhatsappOptin, service, stylist, date, slot }) {
  return (
    <div>
      <h2 className="font-serif text-3xl sm:text-4xl mb-2">Your details</h2>
      <p className="text-stone-500 mb-10 max-w-xl">
        We&apos;ll use this only to confirm your booking.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
        <div className="space-y-6">
          <div>
            <Label htmlFor="name" className="text-xs uppercase tracking-[0.2em] text-stone-500">
              Full name
            </Label>
            <Input
              id="name"
              data-testid="input-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Jane Doe"
              className="mt-2 rounded-none border-stone-300 bg-white h-12 focus-visible:ring-stone-900"
            />
          </div>
          <div>
            <Label htmlFor="phone" className="text-xs uppercase tracking-[0.2em] text-stone-500">
              Phone (verified)
            </Label>
            <Input
              id="phone"
              data-testid="input-phone"
              value={phone}
              readOnly
              aria-readonly="true"
              className="mt-2 rounded-none border-stone-300 bg-stone-50 text-stone-600 h-12 focus-visible:ring-stone-900 cursor-not-allowed"
            />
            <p className="mt-1 text-[11px] text-stone-500">Verified via WhatsApp OTP at login.</p>
          </div>
          <div>
            <Label htmlFor="notes" className="text-xs uppercase tracking-[0.2em] text-stone-500">
              Notes (optional)
            </Label>
            <Textarea
              id="notes"
              data-testid="input-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Anything we should know?"
              className="mt-2 rounded-none border-stone-300 bg-white min-h-[100px] focus-visible:ring-stone-900"
            />
          </div>

          <label
            className="flex items-start gap-3 border border-stone-200 bg-white p-4 cursor-pointer hover:border-stone-400 transition-colors"
            data-testid="whatsapp-optin-label"
          >
            <input
              type="checkbox"
              checked={whatsappOptin}
              onChange={(e) => setWhatsappOptin(e.target.checked)}
              data-testid="whatsapp-optin-checkbox"
              className="mt-1 h-4 w-4 accent-stone-900 cursor-pointer"
            />
            <span className="text-sm text-stone-700 leading-snug">
              Send me a <span className="font-medium">WhatsApp confirmation</span> on this number.
              <span className="block text-xs text-stone-500 mt-1">
                Use international format (e.g. +91 98255 12345).
              </span>
            </span>
          </label>
        </div>

        <SummaryCard service={service} stylist={stylist} date={date} slot={slot} />
      </div>
    </div>
  );
}

function SummaryCard({ service, stylist, date, slot }) {
  return (
    <aside
      className="border border-stone-200 bg-white p-8 h-fit"
      data-testid="summary-card"
    >
      <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-6">Your booking</p>

      <div className="space-y-5">
        <Row label="Service" value={service?.name} sub={`${service?.duration_min} min`} />
        <Row label="Stylist" value={stylist?.name} sub={stylist?.title} />
        <Row
          label="Date"
          value={date ? format(date, "EEEE, d MMMM yyyy") : "—"}
          icon={<CalendarIcon className="h-4 w-4 text-stone-400" strokeWidth={1.25} />}
        />
        <Row
          label="Time"
          value={slot ? `${to12h(slot.start_time)} — ${to12h(slot.end_time)}` : "—"}
          icon={<Clock className="h-4 w-4 text-stone-400" strokeWidth={1.25} />}
        />
      </div>

      <div className="mt-8 pt-6 border-t border-stone-200 flex items-center justify-between">
        <span className="text-xs uppercase tracking-[0.25em] text-stone-500">Total</span>
        <span className="font-serif text-2xl" data-testid="summary-total">
          {service ? `₹${service.price}` : "—"}
        </span>
      </div>
    </aside>
  );
}

function Row({ label, value, sub, icon }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p>
      <div className="flex items-center gap-2">
        {icon}
        <p className="font-serif text-lg leading-tight">{value || "—"}</p>
      </div>
      {sub && <p className="text-xs text-stone-500 mt-1">{sub}</p>}
    </div>
  );
}

/* ============================================================ */
/* Footer (nav)                                                 */
/* ============================================================ */
function Footer({ step, canProceed, onBack, onNext, submitting, isLast, sticky }) {
  if (sticky) {
    return (
      <div
        className="fixed inset-x-0 bottom-0 z-40 bg-[#FAF9F6] border-t border-stone-200 shadow-[0_-4px_16px_rgba(0,0,0,0.04)]"
        data-testid="booking-footer"
      >
        <div className="max-w-5xl mx-auto px-6 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] md:py-4 md:pb-4 flex items-center justify-between gap-4">
          <FooterButtons
            step={step}
            canProceed={canProceed}
            onBack={onBack}
            onNext={onNext}
            submitting={submitting}
            isLast={isLast}
          />
        </div>
      </div>
    );
  }
  return (
    <div
      className="mt-16 pt-6 border-t border-stone-200 flex items-center justify-between gap-4"
      data-testid="booking-footer"
    >
      <FooterButtons
        step={step}
        canProceed={canProceed}
        onBack={onBack}
        onNext={onNext}
        submitting={submitting}
        isLast={isLast}
      />
    </div>
  );
}

function FooterButtons({ step, canProceed, onBack, onNext, submitting, isLast }) {
  return (
    <>
      <button
        type="button"
        onClick={onBack}
        disabled={step === 0}
        data-testid="btn-back"
        className="inline-flex items-center gap-2 text-sm uppercase tracking-[0.2em] text-stone-700 hover:text-stone-900 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronLeft className="h-4 w-4" /> Back
      </button>

      <button
        type="button"
        onClick={onNext}
        disabled={!canProceed || submitting}
        data-testid={isLast ? "btn-confirm" : "btn-next"}
        className={`inline-flex items-center gap-2 px-8 py-4 uppercase tracking-[0.15em] text-sm font-light transition-colors ${
          !canProceed || submitting
            ? "bg-stone-200 text-stone-400 cursor-not-allowed"
            : "bg-stone-900 text-white hover:bg-stone-800"
        }`}
      >
        {isLast ? (submitting ? "Confirming…" : "Confirm booking") : "Continue"}
        {!isLast && <ChevronRight className="h-4 w-4" />}
      </button>
    </>
  );
}

/* ============================================================ */
/* Confirmation Screen                                          */
/* ============================================================ */
function ConfirmationScreen({ data, onReset }) {
  const { booking, service, stylist } = data;
  const formattedDate = format(new Date(booking.date + "T00:00:00"), "EEEE, d MMMM yyyy");

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16" data-testid="confirmation-screen">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-12 step-enter">
          <div className="inline-flex items-center justify-center w-14 h-14 border border-stone-900 mb-6">
            <Check className="h-6 w-6 text-stone-900" strokeWidth={1.5} />
          </div>
          <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-4">Booking Confirmed</p>
          <h1 className="font-serif text-4xl sm:text-5xl tracking-tight mb-4">
            We&apos;ll see you soon, {booking.customer_name.split(" ")[0]}.
          </h1>
          <p className="text-stone-500 max-w-md mx-auto">
            A confirmation has been recorded. Please arrive 5 minutes early to settle in.
          </p>
        </div>

        <div className="border border-stone-200 bg-white p-8 sm:p-10">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-6 gap-x-10">
            <DetailLine label="Reference" value={booking.id.slice(0, 8).toUpperCase()} />
            <DetailLine label="Service" value={service.name} sub={`${service.duration_min} min`} />
            <DetailLine label="Stylist" value={stylist.name} sub={stylist.title} />
            <DetailLine label="Date" value={formattedDate} />
            <DetailLine label="Time" value={`${to12h(booking.start_time)} — ${to12h(booking.end_time)}`} />
            <DetailLine label="Total" value={`₹${service.price}`} />
            <DetailLine label="Name" value={booking.customer_name} icon={<User className="h-4 w-4 text-stone-400" strokeWidth={1.25} />} />
            <DetailLine label="Phone" value={booking.customer_phone} icon={<PhoneIcon className="h-4 w-4 text-stone-400" strokeWidth={1.25} />} />
          </div>

          {booking.notes && (
            <div className="mt-8 pt-6 border-t border-stone-200">
              <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-2">Notes</p>
              <p className="text-sm text-stone-700 leading-relaxed">{booking.notes}</p>
            </div>
          )}

          {booking.manage_url && (
            <div className="mt-8 pt-6 border-t border-stone-200" data-testid="manage-link-panel">
              <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-2">Self-serve changes</p>
              <p className="text-sm text-stone-600 mb-3">Use this private link to reschedule or cancel without re-entering your details.</p>
              <a href={booking.manage_url} data-testid="booking-manage-link" className="inline-flex items-center justify-center border border-stone-900 bg-stone-900 text-white px-4 py-2 text-xs uppercase tracking-[0.2em]">Manage appointment</a>
            </div>
          )}

          {booking.whatsapp_status && booking.whatsapp_status !== "skipped" && (
            <div className="mt-8 pt-6 border-t border-stone-200" data-testid="whatsapp-status">
              <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-2">WhatsApp</p>
              {booking.whatsapp_status === "sent" && (
                <p className="text-sm text-stone-700">
                  ✓ Confirmation sent to {booking.customer_phone} on WhatsApp.
                </p>
              )}
              {booking.whatsapp_status === "failed" && (
                <p className="text-sm text-stone-500">
                  We couldn&apos;t send the WhatsApp message right now — your booking is still confirmed.
                </p>
              )}
              {booking.whatsapp_status === "pending" && (
                <p className="text-sm text-stone-500">WhatsApp confirmation is on its way.</p>
              )}
            </div>
          )}
        </div>

        <div className="mt-10 flex flex-col sm:flex-row gap-4 sm:items-center sm:justify-between">
          <a
            href="/salon"
            data-testid="btn-back-to-salon"
            className="inline-flex items-center gap-2 text-sm uppercase tracking-[0.2em] text-stone-700 hover:text-stone-900"
          >
            <ArrowLeft className="h-4 w-4" /> Back to Salon
          </a>
          <p className="text-xs text-stone-500 uppercase tracking-[0.2em]">
            The Gentlemen&apos;s Room · 9:00 AM — 9:00 PM daily
          </p>
        </div>
      </div>
    </div>
  );
}

function DetailLine({ label, value, sub, icon }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p>
      <div className="flex items-center gap-2">
        {icon}
        <p className="font-serif text-lg leading-tight">{value}</p>
      </div>
      {sub && <p className="text-xs text-stone-500 mt-1">{sub}</p>}
    </div>
  );
}
