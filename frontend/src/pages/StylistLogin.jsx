import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { ArrowLeft } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StylistLogin() {
  const [stylists, setStylists] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [pin, setPin] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    axios.get(`${API}/stylists`).then((r) => setStylists(r.data)).catch(() => {});
    const saved = localStorage.getItem("stylist_id");
    if (saved) navigate("/stylist/portal", { replace: true });
  }, [navigate]);

  const submit = async () => {
    if (!selectedId || pin.length < 4) return;
    setSubmitting(true);
    try {
      const { data } = await axios.post(`${API}/stylist/login`, { stylist_id: selectedId, pin });
      localStorage.setItem("stylist_id", data.token);
      localStorage.setItem("stylist_name", data.stylist.name);
      toast.success(`Welcome, ${data.stylist.name.split(" ")[0]}`);
      navigate("/stylist/portal");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-16">
      <div className="max-w-md w-full">
        <button onClick={() => navigate("/")} data-testid="link-home" className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-stone-500 hover:text-stone-900 mb-10">
          <ArrowLeft className="h-3 w-3" /> Customer Site
        </button>

        <p className="text-xs uppercase tracking-[0.3em] text-stone-500 mb-4">The Gentlemen&apos;s Room</p>
        <h1 className="font-serif text-4xl mb-2">Stylist Portal</h1>
        <p className="text-stone-500 mb-10">Select your name and enter your PIN.</p>

        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-3" data-testid="stylist-options">
            {stylists.map((s) => {
              const sel = selectedId === s.id;
              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setSelectedId(s.id)}
                  data-testid={`stylist-option-${s.id}`}
                  className={`flex items-center gap-4 p-3 border bg-white text-left transition-colors ${sel ? "border-stone-900 ring-1 ring-stone-900" : "border-stone-200 hover:border-stone-900"}`}
                >
                  <img src={s.photo} alt={s.name} className={`w-14 h-14 object-cover ${sel ? "" : "grayscale"}`} />
                  <div>
                    <p className="font-serif text-lg leading-tight">{s.name}</p>
                    <p className="text-xs uppercase tracking-[0.2em] text-stone-500 mt-1">{s.title}</p>
                  </div>
                </button>
              );
            })}
          </div>

          {selectedId && (
            <div className="step-enter">
              <p className="text-xs uppercase tracking-[0.2em] text-stone-500 mb-2">4-digit PIN</p>
              <Input
                type="password"
                inputMode="numeric"
                maxLength={6}
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                data-testid="input-pin"
                placeholder="••••"
                className="rounded-none border-stone-300 bg-white h-12 text-lg tracking-[0.5em] focus-visible:ring-stone-900"
              />
            </div>
          )}

          <button
            type="button"
            onClick={submit}
            disabled={!selectedId || pin.length < 4 || submitting}
            data-testid="btn-login"
            className={`w-full py-4 uppercase tracking-[0.15em] text-sm font-light transition-colors ${!selectedId || pin.length < 4 || submitting ? "bg-stone-200 text-stone-400 cursor-not-allowed" : "bg-stone-900 text-white hover:bg-stone-800"}`}
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}
