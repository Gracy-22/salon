import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Upload, ImageOff } from "lucide-react";
import { API, ownerAuthConfig, money } from "./utils";
import { ProfileInput } from "./ui";
import { SalonMenuManager } from "./SalonMenuManager";
import { sanitizePhoneInput, validatePhone10, PHONE_HELPER_TEXT, PHONE_FIELD_LABEL } from "../../lib/phoneValidation";

const MAX_PHOTO_BYTES = 2 * 1024 * 1024; // 2 MB (must match backend)

const emptyServiceForm = { name: "", category: "Hair", duration_min: 60, price: 1500, description: "", icon: "Scissors", is_active: true };
const emptyStylistForm = { name: "", title: "Stylist", bio: "", photo: "", phone: "", services: [], salon_id: "", is_active: true };

export function StaffTreatmentsManager({ ownerToken, salons = [], salonFilter }) {
  const [services, setServices] = useState([]);
  const [stylists, setStylists] = useState([]);
  const [serviceForm, setServiceForm] = useState(emptyServiceForm);
  const [stylistForm, setStylistForm] = useState(emptyStylistForm);
  const [editingService, setEditingService] = useState(null);
  const [editingStylist, setEditingStylist] = useState(null);

  const activeSalons = salons.filter((s) => s.is_active !== false);
  const defaultSalonId = salonFilter || activeSalons[0]?.id || "salon-main";
  const [menuSalonId, setMenuSalonId] = useState(defaultSalonId);
  useEffect(() => { setMenuSalonId(defaultSalonId); }, [defaultSalonId]);

  const load = useCallback(() => {
    axios.get(`${API}/owner/services`, ownerAuthConfig(ownerToken)).then((r) => setServices(r.data.services || []));
    const stylistParams = salonFilter ? { salon_id: salonFilter } : {};
    axios.get(`${API}/owner/stylists`, { params: stylistParams, ...ownerAuthConfig(ownerToken) }).then((r) => setStylists(r.data.stylists || []));
  }, [ownerToken, salonFilter]);
  useEffect(() => { load(); }, [load]);

  const resetService = () => { setEditingService(null); setServiceForm(emptyServiceForm); };
  const resetStylist = () => { setEditingStylist(null); setStylistForm({ ...emptyStylistForm, salon_id: defaultSalonId }); };

  useEffect(() => {
    setStylistForm((current) => current.salon_id ? current : { ...current, salon_id: defaultSalonId });
  }, [defaultSalonId]);

  const saveService = async () => {
    if (!serviceForm.name.trim()) return toast.error("Treatment name is required");
    const payload = { ...serviceForm, duration_min: Number(serviceForm.duration_min), price: Number(serviceForm.price) };
    try {
      if (editingService) await axios.patch(`${API}/owner/services/${editingService}`, payload, ownerAuthConfig(ownerToken));
      else await axios.post(`${API}/owner/services`, payload, ownerAuthConfig(ownerToken));
      toast.success(editingService ? "Treatment updated" : "Treatment added");
      resetService(); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const archiveService = async (id) => {
    if (!window.confirm("Archive this treatment? It will be hidden from booking and removed from staff assignments.")) return;
    try {
      await axios.post(`${API}/owner/services/${id}/archive`, {}, ownerAuthConfig(ownerToken));
      toast.success("Treatment archived"); load();
    } catch (e) { toast.error("Archive failed"); }
  };
  const saveStylist = async () => {
    if (!stylistForm.name.trim()) return toast.error("Staff name is required");
    const phoneErr = validatePhone10(stylistForm.phone);
    if (phoneErr) return toast.error(phoneErr);
    // Send the single phone as both `phone` and `login_phone` — backend unchanged.
    const payload = {
      ...stylistForm,
      phone: stylistForm.phone,
      login_phone: stylistForm.phone,
      services: stylistForm.services || [],
    };
    try {
      if (editingStylist) await axios.patch(`${API}/owner/stylists/${editingStylist}`, payload, ownerAuthConfig(ownerToken));
      else await axios.post(`${API}/owner/stylists`, payload, ownerAuthConfig(ownerToken));
      toast.success(editingStylist ? "Staff updated" : "Staff added");
      resetStylist(); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Save failed"); }
  };
  const archiveStylist = async (id) => {
    if (!window.confirm("Archive this staff member? Existing booking history will remain.")) return;
    try {
      await axios.post(`${API}/owner/stylists/${id}/archive`, {}, ownerAuthConfig(ownerToken));
      toast.success("Staff archived"); load();
    } catch (e) { toast.error("Archive failed"); }
  };
  const deleteStylist = async (id, name) => {
    if (!window.confirm(`Permanently delete ${name || "this staff member"}? This cannot be undone. Their booking history will remain for records.`)) return;
    try {
      await axios.delete(`${API}/owner/stylists/${id}`, ownerAuthConfig(ownerToken));
      if (editingStylist === id) resetStylist();
      toast.success("Staff deleted"); load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Delete failed"); }
  };
  const deleteStylistsBulk = async (ids) => {
    if (!ids || ids.length === 0) return;
    if (!window.confirm(`Permanently delete ${ids.length} staff member${ids.length === 1 ? "" : "s"}? This cannot be undone.`)) return;
    try {
      const results = await Promise.allSettled(
        ids.map((id) => axios.delete(`${API}/owner/stylists/${id}`, ownerAuthConfig(ownerToken)))
      );
      const failed = results.filter((r) => r.status === "rejected").length;
      if (ids.includes(editingStylist)) resetStylist();
      if (failed === 0) toast.success(`${ids.length} staff deleted`);
      else if (failed < ids.length) toast.warning(`${ids.length - failed} deleted, ${failed} failed`);
      else toast.error("Bulk delete failed");
      load();
    } catch (e) { toast.error("Bulk delete failed"); }
  };

  const activeServices = services.filter((s) => s.is_active !== false);
  const serviceOptions = activeServices.map((s) => ({ value: s.id, label: `${s.name} · ${money(s.price)} · ${s.duration_min}m` }));

  return (
    <section data-testid="owner-staff-treatments">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Team setup</p>
        <h2 className="font-serif text-3xl mt-1">Staff & Treatments</h2>
        <p className="text-sm text-stone-500 mt-2">Archive instead of deleting, so old bookings keep their history.</p>
      </div>
      <div className="grid grid-cols-1 2xl:grid-cols-2 gap-6">
        <TreatmentManager services={services} form={serviceForm} setForm={setServiceForm} editing={editingService} setEditing={setEditingService} onSave={saveService} onArchive={archiveService} onReset={resetService} />
        <StylistManager ownerToken={ownerToken} salons={activeSalons} stylists={stylists} form={stylistForm} setForm={setStylistForm} editing={editingStylist} setEditing={setEditingStylist} onSave={saveStylist} onArchive={archiveStylist} onDelete={deleteStylist} onBulkDelete={deleteStylistsBulk} onReset={resetStylist} serviceOptions={serviceOptions} />
        <SalonMenuManager ownerToken={ownerToken} salons={activeSalons} selectedSalonId={menuSalonId} onSelectSalonId={setMenuSalonId} />
      </div>
    </section>
  );
}

function TreatmentManager({ services, form, setForm, editing, setEditing, onSave, onArchive, onReset }) {
  return (
    <section className="border border-stone-200 bg-white p-6" data-testid="owner-treatment-manager">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Treatments</p>
        {editing && <button onClick={onReset} className="text-xs uppercase tracking-[0.2em] text-stone-500">New</button>}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-5">
        <ProfileInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} testid="service-name-input" />
        <ProfileInput label="Category" value={form.category} onChange={(v) => setForm({ ...form, category: v })} testid="service-category-input" />
        <ProfileInput label="Duration min" type="number" value={form.duration_min} onChange={(v) => setForm({ ...form, duration_min: v })} testid="service-duration-input" />
        <ProfileInput label="Price" type="number" value={form.price} onChange={(v) => setForm({ ...form, price: v })} testid="service-price-input" />
        <ProfileInput label="Icon" value={form.icon} onChange={(v) => setForm({ ...form, icon: v })} testid="service-icon-input" />
        <label className="flex items-center gap-2 text-sm text-stone-600 pt-7">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} data-testid="service-active-input" /> Active
        </label>
        <div className="sm:col-span-2"><ProfileInput label="Description" value={form.description} onChange={(v) => setForm({ ...form, description: v })} testid="service-description-input" textarea /></div>
      </div>
      <button onClick={onSave} data-testid="save-service-button" className="bg-stone-900 text-white px-4 py-3 text-xs uppercase tracking-[0.2em]">{editing ? "Save treatment" : "Add treatment"}</button>
      <div className="mt-6 space-y-2 max-h-[32rem] overflow-auto">
        {services.map((s) => (
          <div key={s.id} className={`border p-3 ${s.is_active === false ? "border-stone-100 bg-stone-50 opacity-70" : "border-stone-200"}`} data-testid={`service-row-${s.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-serif text-xl">{s.name}</p>
                <p className="text-xs text-stone-500">{s.category} · {money(s.price)} · {s.duration_min}m · {s.icon}</p>
                <p className="text-xs text-stone-400 mt-1">{s.is_active === false ? "Archived" : "Active"}</p>
              </div>
              <div className="flex gap-2">
                <button onClick={() => { setEditing(s.id); setForm({ name: s.name, category: s.category, duration_min: s.duration_min, price: s.price, description: s.description || "", icon: s.icon || "Scissors", is_active: s.is_active !== false }); }} className="text-xs uppercase tracking-[0.15em]">Edit</button>
                {s.is_active !== false && <button onClick={() => onArchive(s.id)} className="text-xs uppercase tracking-[0.15em] text-rose-700">Archive</button>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function StylistManager({ ownerToken, salons = [], stylists, form, setForm, editing, setEditing, onSave, onArchive, onDelete, onBulkDelete, onReset, serviceOptions }) {
  const salonNameById = Object.fromEntries(salons.map((s) => [s.id, s.name]));
  const [selected, setSelected] = useState(new Set());
  // If a row disappears (e.g., after bulk delete), drop it from the selection set.
  useEffect(() => {
    const validIds = new Set(stylists.map((s) => s.id));
    setSelected((prev) => {
      const next = new Set([...prev].filter((id) => validIds.has(id)));
      return next.size === prev.size ? prev : next;
    });
  }, [stylists]);
  const toggleOne = (id) => setSelected((prev) => {
    const next = new Set(prev); if (next.has(id)) next.delete(id); else next.add(id); return next;
  });
  const allSelected = stylists.length > 0 && selected.size === stylists.length;
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(stylists.map((s) => s.id)));
  return (
    <section className="border border-stone-200 bg-white p-6" data-testid="owner-staff-manager">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Staff</p>
        {editing && <button onClick={onReset} className="text-xs uppercase tracking-[0.2em] text-stone-500">New</button>}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-4 mb-5">
        <StylistPhotoPicker ownerToken={ownerToken} value={form.photo} onChange={(v) => setForm({ ...form, photo: v })} />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <ProfileInput label="Name" value={form.name} onChange={(v) => setForm({ ...form, name: v })} testid="stylist-name-input" />
          <ProfileInput label="Title" value={form.title} onChange={(v) => setForm({ ...form, title: v })} testid="stylist-title-input" />
          {salons.length > 0 && (
            <label className="sm:col-span-2 block">
              <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Salon</p>
              <select value={form.salon_id || ""} onChange={(e) => setForm({ ...form, salon_id: e.target.value })} data-testid="stylist-salon-select" className="w-full border border-stone-300 px-3 py-2 bg-white">
                {salons.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </label>
          )}
          <div className="sm:col-span-2">
            <ProfileInput
              label={PHONE_FIELD_LABEL}
              value={form.phone}
              onChange={(v) => setForm({ ...form, phone: sanitizePhoneInput(v) })}
              testid="stylist-phone-input"
            />
            <p className="mt-1 text-[11px] text-stone-500" data-testid="stylist-phone-helper">{PHONE_HELPER_TEXT}</p>
            {validatePhone10(form.phone, { allowEmpty: true }) && (
              <p className="mt-1 text-[11px] text-rose-600" data-testid="stylist-phone-error">{validatePhone10(form.phone, { allowEmpty: true })}</p>
            )}
          </div>
          <div className="sm:col-span-2"><ProfileInput label="Bio" value={form.bio} onChange={(v) => setForm({ ...form, bio: v })} testid="stylist-bio-input" textarea /></div>
          <label className="flex items-center gap-2 text-sm text-stone-600">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} data-testid="stylist-active-input" /> Active
          </label>
        </div>
      </div>
      <MultiServicePicker options={serviceOptions} value={form.services} onChange={(servicesValue) => setForm({ ...form, services: servicesValue })} />
      <button onClick={onSave} data-testid="save-stylist-button" className="mt-5 bg-stone-900 text-white px-4 py-3 text-xs uppercase tracking-[0.2em]">{editing ? "Save staff" : "Add staff"}</button>      <div className="mt-6 space-y-2 max-h-[32rem] overflow-auto">
        {stylists.length > 0 && (
          <div className="flex items-center justify-between border border-stone-200 bg-stone-50 px-3 py-2 sticky top-0 z-10" data-testid="staff-bulk-bar">
            <label className="flex items-center gap-2 text-xs uppercase tracking-[0.15em] text-stone-600 cursor-pointer">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={toggleAll}
                data-testid="staff-bulk-select-all"
                className="accent-stone-900"
              />
              {selected.size > 0 ? `${selected.size} selected` : "Select all"}
            </label>
            {selected.size > 0 && (
              <button
                onClick={() => onBulkDelete([...selected])}
                data-testid="staff-bulk-delete-button"
                className="text-xs uppercase tracking-[0.15em] px-3 py-1.5 bg-rose-900 text-white hover:bg-rose-800"
              >
                Delete {selected.size}
              </button>
            )}
          </div>
        )}
        {stylists.map((s) => (
          <div key={s.id} className={`border p-3 ${selected.has(s.id) ? "border-stone-900 bg-stone-50" : s.is_active === false ? "border-stone-100 bg-stone-50 opacity-70" : "border-stone-200"}`} data-testid={`stylist-row-${s.id}`}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={selected.has(s.id)}
                  onChange={() => toggleOne(s.id)}
                  data-testid={`staff-select-${s.id}`}
                  className="mt-2 accent-stone-900"
                  aria-label={`Select ${s.name}`}
                />
                <StylistAvatar photo={s.photo} name={s.name} />
                <div>
                  <p className="font-serif text-xl">{s.name}</p>
                  <p className="text-xs text-stone-500">{s.title} · {s.phone || s.login_phone || "no mobile"}</p>
                  <p className="text-xs text-stone-400 mt-1">{salonNameById[s.salon_id] || "Unassigned salon"} · {s.is_active === false ? "Archived" : "Active"} · {(s.services || []).length} treatments</p>
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => { setEditing(s.id); setForm({ name: s.name, title: s.title || "Stylist", bio: s.bio || "", photo: s.photo || "", phone: s.phone || s.login_phone || "", services: s.services || [], salon_id: s.salon_id || "", is_active: s.is_active !== false }); }} className="text-xs uppercase tracking-[0.15em]">Edit</button>
                {s.is_active !== false && <button onClick={() => onArchive(s.id)} className="text-xs uppercase tracking-[0.15em] text-rose-700">Archive</button>}
                <button onClick={() => onDelete(s.id, s.name)} data-testid={`delete-stylist-${s.id}`} className="text-xs uppercase tracking-[0.15em] text-rose-900 hover:underline">Delete</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function MultiServicePicker({ options, value, onChange }) {
  const selected = new Set(value || []);
  const toggle = (id) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    onChange(Array.from(next));
  };
  return (
    <div data-testid="stylist-service-picker">
      <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-2">Treatments this staff can perform</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-44 overflow-auto border border-stone-200 p-3">
        {options.map((option) => (
          <label key={option.value} className="flex items-center gap-2 text-xs text-stone-600">
            <input type="checkbox" checked={selected.has(option.value)} onChange={() => toggle(option.value)} data-testid={`stylist-service-${option.value}`} /> {option.label}
          </label>
        ))}
      </div>
    </div>
  );
}

function StylistAvatar({ photo, name }) {
  const initials = (name || "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  if (photo) {
    return <img src={photo} alt={name} className="h-12 w-12 object-cover border border-stone-200" />;
  }
  return (
    <div className="h-12 w-12 border border-stone-200 bg-stone-100 text-stone-500 flex items-center justify-center text-xs font-medium">
      {initials || <ImageOff className="h-4 w-4" />}
    </div>
  );
}

function StylistPhotoPicker({ ownerToken, value, onChange }) {
  const inputRef = useRef(null);
  const [urlMode, setUrlMode] = useState(false);
  const [uploading, setUploading] = useState(false);

  const onFile = async (file) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Please choose an image file");
      return;
    }
    if (file.size > MAX_PHOTO_BYTES) {
      toast.error("Image must be 2 MB or smaller");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    setUploading(true);
    try {
      const { data } = await axios.post(`${API}/owner/uploads/image`, fd, ownerAuthConfig(ownerToken));
      onChange(data.url);
      toast.success("Photo uploaded");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div data-testid="stylist-photo-picker">
      <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-2">Photo</p>
      <div className="w-32 h-32 border border-stone-300 bg-stone-50 overflow-hidden flex items-center justify-center mb-2">
        {uploading
          ? <span className="text-[10px] uppercase tracking-[0.15em] text-stone-500" data-testid="stylist-photo-uploading">Uploading…</span>
          : value
            ? <img src={value} alt="Stylist preview" className="w-full h-full object-cover" data-testid="stylist-photo-preview" />
            : <ImageOff className="h-6 w-6 text-stone-400" data-testid="stylist-photo-empty" />}
      </div>
      <div className="flex flex-col gap-1.5">
        <input ref={inputRef} type="file" accept="image/*" onChange={(e) => onFile(e.target.files?.[0])} className="hidden" data-testid="stylist-photo-file-input" />
        <button type="button" onClick={() => inputRef.current?.click()} disabled={uploading} className="inline-flex items-center justify-center gap-1.5 border border-stone-300 px-2 py-1.5 text-[10px] uppercase tracking-[0.15em] hover:border-stone-900 disabled:opacity-50" data-testid="stylist-photo-upload-button">
          <Upload className="h-3 w-3" /> Upload
        </button>
        <button type="button" onClick={() => setUrlMode((v) => !v)} className="text-[10px] uppercase tracking-[0.15em] text-stone-500 hover:text-stone-900" data-testid="stylist-photo-url-toggle">
          {urlMode ? "Hide URL" : "Paste URL"}
        </button>
        {urlMode && (
          <input type="url" value={value || ""} onChange={(e) => onChange(e.target.value)} placeholder="https://…" className="w-full border border-stone-300 px-2 py-1.5 text-xs" data-testid="stylist-photo-url-input" />
        )}
        {value && !uploading && (
          <button type="button" onClick={() => onChange("")} className="text-[10px] uppercase tracking-[0.15em] text-rose-700 hover:text-rose-900" data-testid="stylist-photo-clear-button">
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
