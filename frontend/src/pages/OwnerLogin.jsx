import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import SearchableSelect from "@/components/SearchableSelect";
import OtpBoxes from "@/components/OtpBoxes";
import { ArrowLeft, ShieldCheck } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const COUNTRIES = [
  { code: "+91", name: "India", flag: "IN" },
  { code: "+1", name: "United States", flag: "US" },
  { code: "+44", name: "United Kingdom", flag: "GB" },
  { code: "+971", name: "United Arab Emirates", flag: "AE" },
  { code: "+61", name: "Australia", flag: "AU" },
  { code: "+65", name: "Singapore", flag: "SG" },
];

export default function OwnerLogin() {
  const [countryCode, setCountryCode] = useState("+91");
  const [phone, setPhone] = useState("8511111593");
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState(false);
  const [otpRequested, setOtpRequested] = useState(false);
  const [resendIn, setResendIn] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (resendIn <= 0) return undefined;
    const timer = window.setTimeout(() => setResendIn((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [resendIn]);

  const navigate = useNavigate();

  const countryOptions = COUNTRIES.map((country) => ({ value: country.code, label: `${country.flag} ${country.name} ${country.code}`, search: `${country.name} ${country.code} ${country.flag}` }));

  const fullPhone = `${countryCode}${phone.replace(/\D/g, "")}`;

  const completeLogin = (token) => {
    localStorage.setItem("owner_token", token);
    navigate("/owner/dashboard");
  };

  const requestOtp = async () => {
    if (phone.replace(/\D/g, "").length < 6) return toast.error("Enter your mobile number");
    setSubmitting(true);
    try {
      await axios.post(`${API}/owner/login/request-otp`, { phone: fullPhone });
      const isResend = otpRequested;
      setOtpRequested(true);
      setResendIn(15);
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
      const { data } = await axios.post(`${API}/owner/login/verify-otp`, { phone: fullPhone, otp: otpToSend });
      completeLogin(data.token);
    } catch (e) {
      setOtpError(true);
      setOtp("");
      window.setTimeout(() => setOtpError(false), 600);
      toast.error(e?.response?.data?.detail || "Invalid OTP");
    } finally { setSubmitting(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16">
      <div className="max-w-md w-full">
        <button onClick={() => navigate("/")} className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-stone-500 hover:text-stone-900 mb-10"><ArrowLeft className="h-3 w-3" /> Customer Site</button>
        <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-4">The Gentlemen&apos;s Room</p>
        <h1 className="font-serif text-4xl mb-2">Owner Sign In</h1>
        <p className="text-stone-500 mb-8">Use WhatsApp OTP to access the owner dashboard.</p>

        <div data-testid="owner-otp-login-panel">
          {!otpRequested ? (
            <div className="grid grid-cols-[140px_1fr] gap-3 mb-4">
              <SearchableSelect label="Country" options={countryOptions} value={countryCode} onChange={setCountryCode} placeholder="Country" testid="owner-country-select" />
              <label>
                <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Mobile number</p>
                <Input value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ""))} data-testid="owner-phone-input" placeholder="8511111593" className="rounded-none border-stone-300 bg-white h-11" />
              </label>
            </div>
          ) : (
            <div className="mb-4 border border-stone-200 bg-stone-50 px-4 py-3" data-testid="owner-phone-locked">
              <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">OTP sent to</p>
              <p className="font-medium text-stone-800">{fullPhone}</p>
            </div>
          )}
          {!otpRequested ? (
            <button type="button" onClick={requestOtp} disabled={submitting} data-testid="owner-request-otp" className="w-full py-4 uppercase tracking-[0.15em] text-sm font-light bg-stone-900 text-white hover:bg-stone-800 disabled:opacity-50">
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
                  testidPrefix="owner-otp"
                />
              </div>
              <button type="button" onClick={() => verifyOtp()} disabled={otp.length < 6 || submitting} data-testid="owner-verify-otp" className="w-full py-4 uppercase tracking-[0.15em] text-sm font-light bg-stone-900 text-white hover:bg-stone-800 disabled:opacity-50 transition-colors">
                {submitting ? "Verifying…" : "Verify & sign in"}
              </button>
              <button type="button" onClick={requestOtp} disabled={submitting || resendIn > 0} data-testid="owner-resend-otp" className="mt-3 w-full text-xs uppercase tracking-[0.2em] text-stone-500 hover:text-stone-900 disabled:text-stone-300 disabled:cursor-not-allowed">
                {resendIn > 0 ? `Resend OTP in ${resendIn}s` : "Resend OTP"}
              </button>
              <button type="button" onClick={() => { setOtpRequested(false); setOtp(""); setOtpError(false); setResendIn(0); }} className="mt-3 w-full text-xs uppercase tracking-[0.2em] text-stone-500 hover:text-stone-900">Change number</button>
            </div>
          )}
          <p className="mt-4 flex items-center gap-2 text-xs text-stone-500"><ShieldCheck className="h-3 w-3" /> OTP has been sent on WhatsApp.</p>
        </div>
      </div>
    </div>
  );
}
