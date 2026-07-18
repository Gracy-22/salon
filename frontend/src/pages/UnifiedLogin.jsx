import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, LogIn, ShieldCheck } from "lucide-react";
import { Input } from "@/components/ui/input";
import SearchableSelect from "@/components/SearchableSelect";
import OtpBoxes from "@/components/OtpBoxes";
import { sanitizePhoneInput, validatePhone10 } from "../lib/phoneValidation";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const COUNTRIES = [
  { code: "+91", name: "India", flag: "IN" },
  { code: "+1", name: "United States", flag: "US" },
  { code: "+44", name: "United Kingdom", flag: "GB" },
  { code: "+971", name: "United Arab Emirates", flag: "AE" },
  { code: "+61", name: "Australia", flag: "AU" },
  { code: "+65", name: "Singapore", flag: "SG" },
];

export default function UnifiedLogin() {
  const [countryCode, setCountryCode] = useState("+91");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState(false);
  const [otpRequested, setOtpRequested] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resendIn, setResendIn] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    if (resendIn <= 0) return undefined;
    const timer = window.setTimeout(() => setResendIn((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [resendIn]);


  const countryOptions = COUNTRIES.map((country) => ({ value: country.code, label: `${country.flag} ${country.name} ${country.code}`, search: `${country.name} ${country.code} ${country.flag}` }));
  const isIndia = countryCode === "+91";
  const digits = phone.replace(/\D/g, "");
  const phoneError = isIndia ? validatePhone10(phone, { allowEmpty: true }) : (digits.length && digits.length < 6 ? "Enter a valid mobile number" : "");
  const canRequestOtp = isIndia ? digits.length === 10 : digits.length >= 6;
  const fullPhone = `${countryCode}${digits}`;

  const requestOtp = async () => {
    if (isIndia) {
      const err = validatePhone10(phone);
      if (err) return toast.error(err);
    } else if (digits.length < 6) {
      return toast.error("Enter your mobile number");
    }
    setSubmitting(true);
    try {
      await axios.post(`${API}/login/request-otp`, { phone: fullPhone });
      const isResend = otpRequested;
      setOtpRequested(true);
      setResendIn(15);
      // Clear previous digits so the user knows to enter the fresh code
      if (isResend) {
        setOtp("");
        setOtpError(false);
      }
      toast.success(isResend ? "New OTP sent on WhatsApp" : "OTP sent on WhatsApp");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not send OTP");
    } finally { setSubmitting(false); }
  };

  const verifyOtp = async (submittedOtp) => {
    const otpToSend = typeof submittedOtp === "string" ? submittedOtp : otp;
    if (otpToSend.length < 6) return;
    setSubmitting(true);
    setOtpError(false);
    try {
      const { data } = await axios.post(`${API}/login/verify-otp`, { phone: fullPhone, otp: otpToSend });
      if (data.role === "owner") {
        localStorage.setItem("owner_token", data.token);
        navigate("/owner/dashboard");
      } else if (data.role === "manager") {
        localStorage.setItem("manager_token", data.token);
        navigate("/manager/dashboard");
      } else if (data.role === "stylist") {
        localStorage.setItem("stylist_id", data.stylist.id);
        localStorage.setItem("stylist_name", data.stylist.name);
        navigate("/stylist/portal");
      } else {
        localStorage.setItem("customer_phone", data.phone);
        // Persist customer JWT so the dashboard/manage pages can refresh
        // appointments without another OTP round-trip.
        if (data.token) localStorage.setItem("customer_token", data.token);
        try {
          localStorage.setItem("customer_appointments", JSON.stringify(data.appointments || []));
        } catch (_e) { /* storage full – ignore */ }
        // If the user was sent here from a "Book Now" CTA, honour the ?next= redirect;
        // otherwise fall back to the customer dashboard.
        const nextParam = new URLSearchParams(window.location.search).get("next");
        navigate(nextParam && nextParam.startsWith("/") ? nextParam : "/customer");
      }
    } catch (e) {
      setOtpError(true);
      setOtp("");
      window.setTimeout(() => setOtpError(false), 600);
      toast.error(e?.response?.data?.detail || "Invalid OTP");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center px-6 py-16" data-testid="unified-login-page">
      <div className="max-w-md w-full bg-white border border-stone-200 p-8 sm:p-10">
        <Link to="/" className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-stone-500 hover:text-stone-900 mb-8"><ArrowLeft className="h-3 w-3" /> Home</Link>
        <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-4">The Gentlemen&apos;s Room</p>
        <h1 className="font-serif text-4xl mb-2">Login with OTP</h1>
        <p className="text-stone-500 mb-8">Enter your mobile number. We’ll identify whether you are a customer, stylist or owner.</p>
        {!otpRequested ? (
          <div className="grid grid-cols-[140px_1fr] gap-3 mb-4">
            <SearchableSelect label="Country" options={countryOptions} value={countryCode} onChange={setCountryCode} placeholder="Country" testid="login-country-select" />
            <label>
              <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Mobile number</p>
              <Input
                value={phone}
                onChange={(e) => setPhone(isIndia ? sanitizePhoneInput(e.target.value) : e.target.value.replace(/\D/g, ""))}
                data-testid="login-phone-input"
                placeholder={isIndia ? "10-digit mobile" : "Mobile number"}
                inputMode="numeric"
                className={`rounded-none bg-white h-11 ${phoneError ? "border-rose-500 focus-visible:ring-rose-500" : "border-stone-300"}`}
              />
              {phoneError && <p className="mt-1 text-[11px] text-rose-600" data-testid="login-phone-error">{phoneError}</p>}
            </label>
          </div>
        ) : (
          <div className="mb-4 border border-stone-200 bg-stone-50 px-4 py-3" data-testid="login-phone-locked">
            <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">OTP sent to</p>
            <p className="font-medium text-stone-800">{fullPhone}</p>
          </div>
        )}
        {!otpRequested ? (
          <button onClick={requestOtp} disabled={submitting || !canRequestOtp} data-testid="login-request-otp" className="w-full py-4 uppercase tracking-[0.15em] text-sm font-light bg-stone-900 text-white hover:bg-stone-800 disabled:opacity-50">
            {submitting ? "Sending…" : "Send WhatsApp OTP"}
          </button>
        ) : (
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-3">Enter 6-digit code</p>
            <div className="mb-5">
              <OtpBoxes
                value={otp}
                onChange={(v) => { setOtp(v); if (otpError) setOtpError(false); }}
                onComplete={(v) => verifyOtp(v)}
                error={otpError}
                disabled={submitting}
                testidPrefix="login-otp"
              />
            </div>
            <button onClick={() => verifyOtp()} disabled={otp.length < 6 || submitting} data-testid="login-verify-otp" className="w-full py-4 uppercase tracking-[0.15em] text-sm font-light bg-stone-900 text-white hover:bg-stone-800 disabled:opacity-50 transition-colors">
              {submitting ? "Verifying…" : "Continue"}
            </button>
            <button type="button" onClick={requestOtp} disabled={submitting || resendIn > 0} data-testid="login-resend-otp" className="mt-3 w-full text-xs uppercase tracking-[0.2em] text-stone-500 hover:text-stone-900 disabled:text-stone-300 disabled:cursor-not-allowed">
              {resendIn > 0 ? `Resend OTP in ${resendIn}s` : "Resend OTP"}
            </button>
            <button type="button" onClick={() => { setOtpRequested(false); setOtp(""); setOtpError(false); setResendIn(0); }} className="mt-3 w-full text-xs uppercase tracking-[0.2em] text-stone-500 hover:text-stone-900">Change number</button>
          </div>
        )}
        <p className="mt-4 flex items-center gap-2 text-xs text-stone-500"><ShieldCheck className="h-3 w-3" /> OTP has been sent on WhatsApp.</p>
      </div>
    </div>
  );
}
