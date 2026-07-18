import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, ownerAuthConfig } from "./utils";
import { ProfileInput } from "./ui";
import { ManagersManager } from "./ManagersManager";

const emptyForm = { name: "", address: "", city: "", phone: "", timezone: "Asia/Kolkata", booking_window_days: 30, is_active: true };

export function SalonsManager({ ownerToken, onSalonsChanged }) {
  const [salons, setSalons] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [showArchived, setShowArchived] = useState(false);

  const archivedCount = salons.filter((s) => s.is_active === false).length;
  const visibleSalons = showArchived ? salons : salons.filter((s) => s.is_active !== false);

  const load = useCallback(() => {
    axios.get(`${API}/owner/salons`, ownerAuthConfig(ownerToken)).then((r) => setSalons(r.data.salons || []));
  }, [ownerToken]);
  useEffect(() => { load(); }, [load]);

  const reset = () => { setEditing(null); setForm(emptyForm); };

  const save = async () => {
    if (!form.name.trim()) return toast.error("Salon name is required");
    try {
      if (editing) await axios.patch(`${API}/owner/salons/${editing}`, form, ownerAuthConfig(ownerToken));
      else await axios.post(`${API}/owner/salons`, form, ownerAuthConfig(ownerToken));
      toast.success(editing ? "Salon updated" : "Salon added");
      reset();
      load();
      onSalonsChanged?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
  };

  const archive = async (id) => {
    if (!window.confirm("Archive this salon? Existing bookings stay; the salon disappears from new bookings.")) return;
    try {
      await axios.post(`${API}/owner/salons/${id}/archive`, {}, ownerAuthConfig(ownerToken));
      toast.success("Salon archived");
      load();
      onSalonsChanged?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Archive failed");
    }
  };

  return (
    <section data-testid="owner-salons-manager">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Locations</p>
        <h2 className="font-serif text-3xl mt-1">Salons</h2>
        <p className="text-sm text-stone-500 mt-2">Add new locations, set timezone & contact details, archive when closed.</p>
      </div>

      <div className="border border-stone-200 bg-white p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">{editing ? "Edit salon" : "New salon"}</p>
          {editing && <button onClick={reset} className="text-xs uppercase tracking-[0.2em] text-stone-500" data-testid="salon-form-reset">New</button>}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <ProfileInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} testid="salon-name-input" />
          <ProfileInput label="City" value={form.city} onChange={(v) => setForm({ ...form, city: v })} testid="salon-city-input" />
          <div className="sm:col-span-2"><ProfileInput label="Address" value={form.address} onChange={(v) => setForm({ ...form, address: v })} testid="salon-address-input" /></div>
          <ProfileInput label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} testid="salon-phone-input" />
          <ProfileInput label="Timezone" value={form.timezone} onChange={(v) => setForm({ ...form, timezone: v })} testid="salon-timezone-input" />
          <div>
            <label className="text-xs uppercase tracking-[0.18em] text-stone-500">Booking window (days in advance)</label>
            <input
              type="number"
              min={1}
              max={365}
              value={form.booking_window_days}
              onChange={(e) => setForm({ ...form, booking_window_days: Math.max(1, Math.min(365, parseInt(e.target.value, 10) || 30)) })}
              data-testid="salon-booking-window-input"
              className="mt-1 w-full border border-stone-300 px-3 py-2 bg-white text-sm"
            />
            <p className="text-[11px] text-stone-400 mt-1">Customers can book up to this many days ahead (1–365).</p>
          </div>
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} data-testid="salon-active-input" /> Active
          </label>
        </div>
        <button onClick={save} data-testid="save-salon-button" className="bg-stone-900 text-white px-4 py-3 text-xs uppercase tracking-[0.2em]">{editing ? "Save salon" : "Add salon"}</button>
      </div>

      <div className="flex items-center justify-between mb-3">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Locations ({visibleSalons.length})</p>
        {archivedCount > 0 && (
          <label className="flex items-center gap-2 text-xs text-stone-500">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} data-testid="salons-show-archived-toggle" />
            Show archived ({archivedCount})
          </label>
        )}
      </div>

      <div className="space-y-2">
        {visibleSalons.map((s) => (
          <div key={s.id} className={`border p-4 ${s.is_active === false ? "border-stone-100 bg-stone-50 opacity-70" : "border-stone-200 bg-white"}`} data-testid={`salon-row-${s.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-serif text-xl">{s.name}</p>
                <p className="text-xs text-stone-500">{[s.city, s.address].filter(Boolean).join(" · ") || "no address"} · {s.phone || "no phone"} · {s.timezone}</p>
                <p className="text-xs text-stone-400 mt-1">{s.is_active === false ? "Archived" : "Active"} · slug: {s.slug} · books up to {s.booking_window_days || 30}d ahead</p>
              </div>
              <div className="flex gap-3 shrink-0">
                <button onClick={() => { setEditing(s.id); setForm({ name: s.name, address: s.address || "", city: s.city || "", phone: s.phone || "", timezone: s.timezone || "Asia/Kolkata", booking_window_days: s.booking_window_days || 30, is_active: s.is_active !== false }); }} className="text-xs uppercase tracking-[0.15em]" data-testid={`salon-edit-${s.id}`}>Edit</button>
                {s.is_active !== false && s.id !== "salon-main" && <button onClick={() => archive(s.id)} className="text-xs uppercase tracking-[0.15em] text-rose-700" data-testid={`salon-archive-${s.id}`}>Archive</button>}
              </div>
            </div>
          </div>
        ))}
      </div>

      <ManagersManager ownerToken={ownerToken} salons={salons} />
    </section>
  );
}
