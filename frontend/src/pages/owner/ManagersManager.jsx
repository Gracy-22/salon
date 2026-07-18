import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, ownerAuthConfig } from "./utils";
import { ProfileInput } from "./ui";
import { sanitizePhoneInput, validatePhone10, PHONE_HELPER_TEXT, PHONE_FIELD_LABEL } from "../../lib/phoneValidation";

const emptyForm = { name: "", phone: "", salon_id: "", is_active: true };

export function ManagersManager({ ownerToken, salons = [] }) {
  const activeSalons = salons.filter((s) => s.is_active !== false);
  const [managers, setManagers] = useState([]);
  const [form, setForm] = useState({ ...emptyForm, salon_id: activeSalons[0]?.id || "" });
  const [editing, setEditing] = useState(null);
  const [showArchived, setShowArchived] = useState(false);

  const load = useCallback(() => {
    axios.get(`${API}/owner/managers`, ownerAuthConfig(ownerToken)).then((r) => setManagers(r.data.managers || []));
  }, [ownerToken]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    setForm((cur) => (cur.salon_id || !activeSalons[0]) ? cur : { ...cur, salon_id: activeSalons[0].id });
  }, [activeSalons]);

  const reset = () => { setEditing(null); setForm({ ...emptyForm, salon_id: activeSalons[0]?.id || "" }); };
  const salonNameById = Object.fromEntries(salons.map((s) => [s.id, s.name]));

  const save = async () => {
    if (!form.name.trim() || !form.salon_id) return toast.error("Name and salon are required");
    const phoneErr = validatePhone10(form.phone);
    if (phoneErr) return toast.error(phoneErr);
    // Send the single phone value as both `phone` and `login_phone` — backend unchanged.
    const payload = { ...form, phone: form.phone, login_phone: form.phone };
    try {
      if (editing) await axios.patch(`${API}/owner/managers/${editing}`, payload, ownerAuthConfig(ownerToken));
      else await axios.post(`${API}/owner/managers`, payload, ownerAuthConfig(ownerToken));
      toast.success(editing ? "Manager updated" : "Manager added");
      reset();
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    }
  };

  const archive = async (id) => {
    if (!window.confirm("Archive this manager? They will no longer be able to sign in.")) return;
    try {
      await axios.post(`${API}/owner/managers/${id}/archive`, {}, ownerAuthConfig(ownerToken));
      toast.success("Manager archived");
      load();
    } catch (e) { toast.error("Archive failed"); }
  };

  const archivedCount = managers.filter((m) => m.is_active === false).length;
  const visible = showArchived ? managers : managers.filter((m) => m.is_active !== false);

  if (activeSalons.length === 0) return null;

  return (
    <section data-testid="owner-managers-manager" className="mt-10">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Location managers</p>
        <h2 className="font-serif text-3xl mt-1">Managers</h2>
        <p className="text-sm text-stone-500 mt-2">Give each salon a manager. They sign in with WhatsApp OTP and see only their own location&apos;s dashboard.</p>
      </div>

      <div className="border border-stone-200 bg-white p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">{editing ? "Edit manager" : "New manager"}</p>
          {editing && <button onClick={reset} className="text-xs uppercase tracking-[0.2em] text-stone-500" data-testid="manager-form-reset">New</button>}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <ProfileInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} testid="manager-name-input" />
          <label className="block">
            <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Salon</p>
            <select value={form.salon_id} onChange={(e) => setForm({ ...form, salon_id: e.target.value })} data-testid="manager-salon-select" className="w-full border border-stone-300 px-3 py-2 bg-white">
              {activeSalons.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </label>
          <div className="sm:col-span-2">
            <ProfileInput
              label={PHONE_FIELD_LABEL}
              value={form.phone}
              onChange={(v) => setForm({ ...form, phone: sanitizePhoneInput(v) })}
              testid="manager-phone-input"
            />
            <p className="mt-1 text-[11px] text-stone-500" data-testid="manager-phone-helper">{PHONE_HELPER_TEXT}</p>
            {validatePhone10(form.phone, { allowEmpty: true }) && (
              <p className="mt-1 text-[11px] text-rose-600" data-testid="manager-phone-error">{validatePhone10(form.phone, { allowEmpty: true })}</p>
            )}
          </div>
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} data-testid="manager-active-input" /> Active
          </label>
        </div>
        <button onClick={save} data-testid="save-manager-button" className="bg-stone-900 text-white px-4 py-3 text-xs uppercase tracking-[0.2em]">{editing ? "Save manager" : "Add manager"}</button>
      </div>

      <div className="flex items-center justify-between mb-3">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Team ({visible.length})</p>
        {archivedCount > 0 && (
          <label className="flex items-center gap-2 text-xs text-stone-500">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} data-testid="managers-show-archived-toggle" /> Show archived ({archivedCount})
          </label>
        )}
      </div>

      <div className="space-y-2">
        {visible.map((m) => (
          <div key={m.id} className={`border p-4 ${m.is_active === false ? "border-stone-100 bg-stone-50 opacity-70" : "border-stone-200 bg-white"}`} data-testid={`manager-row-${m.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-serif text-xl">{m.name}</p>
                <p className="text-xs text-stone-500">{salonNameById[m.salon_id] || "Unassigned salon"} · {m.phone || m.login_phone || "no phone"}</p>
                <p className="text-xs text-stone-400 mt-1">{m.is_active === false ? "Archived" : "Active"}</p>
              </div>
              <div className="flex gap-3 shrink-0">
                <button onClick={() => { setEditing(m.id); setForm({ name: m.name, phone: m.phone || m.login_phone || "", salon_id: m.salon_id, is_active: m.is_active !== false }); }} className="text-xs uppercase tracking-[0.15em]" data-testid={`manager-edit-${m.id}`}>Edit</button>
                {m.is_active !== false && <button onClick={() => archive(m.id)} className="text-xs uppercase tracking-[0.15em] text-rose-700" data-testid={`manager-archive-${m.id}`}>Archive</button>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
