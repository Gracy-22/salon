import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import SearchableSelect from "@/components/SearchableSelect";
import { API, ownerAuthConfig, money } from "./utils";
import { ProfileStat, ProfileInput } from "./ui";

export function OwnerCustomerDirectory({ ownerToken }) {
  const [customers, setCustomers] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState(null);
  const customerOptions = customers.map((c) => ({ value: c.customer_phone, label: `${c.customer_name || "Customer"} · ${c.customer_phone}`, search: `${c.customer_name || ""} ${c.customer_phone || ""}` }));
  const loadCustomers = useCallback(() => {
    axios.get(`${API}/owner/customers/search`, ownerAuthConfig(ownerToken)).then((r) => {
      const rows = r.data.customers || [];
      setCustomers(rows);
      setSelectedPhone((current) => current || rows[0]?.customer_phone || null);
    });
  }, [ownerToken]);
  useEffect(() => { loadCustomers(); }, [loadCustomers]);
  const selectedCustomer = customers.find((c) => c.customer_phone === selectedPhone);
  return (
    <section data-testid="owner-customer-directory">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Client history</p>
          <h2 className="font-serif text-3xl mt-1">Customer profiles</h2>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        <div className="border border-stone-200 bg-white p-4">
          <SearchableSelect label="Customer" options={customerOptions} value={selectedPhone || ""} onChange={setSelectedPhone} placeholder="Type name or phone" testid="owner-customer-select" emptyLabel="No customers found" />
          <p className="mt-3 text-xs text-stone-500" data-testid="owner-customer-count">{customers.length} customers</p>
          {selectedCustomer && <p className="mt-4 font-serif text-xl" data-testid="owner-selected-customer">{selectedCustomer.customer_name || "Customer"}</p>}
        </div>
        {selectedPhone ? <OwnerCustomerProfilePanel ownerToken={ownerToken} phone={selectedPhone} onSaved={loadCustomers} /> : <p className="text-sm text-stone-500">Select a customer to open a profile.</p>}
      </div>
    </section>
  );
}

function OwnerCustomerProfilePanel({ ownerToken, phone, onSaved }) {
  const [profile, setProfile] = useState(null);
  const [stylists, setStylists] = useState([]);
  const [form, setForm] = useState({});
  const loadProfile = useCallback(() => {
    axios.get(`${API}/owner/customers/${phone}`, ownerAuthConfig(ownerToken)).then((r) => {
      setProfile(r.data);
      setForm({ customer_phone: r.data.customer_phone, customer_name: r.data.customer_name || "", birthday: r.data.birthday || "", hair_type: r.data.hair_type || "", product_allergies: r.data.product_allergies || "", preferences: r.data.preferences || "", stylist_notes: r.data.stylist_notes || "", preferred_stylist_id: r.data.preferred_stylist_manual ? r.data.preferred_stylist_id : "" });
    });
  }, [ownerToken, phone]);
  useEffect(() => { loadProfile(); axios.get(`${API}/stylists`).then((r) => setStylists(r.data || [])); }, [loadProfile]);
  const save = async () => {
    await axios.patch(`${API}/owner/customers/${phone}`, form, ownerAuthConfig(ownerToken));
    toast.success("Customer profile saved");
    loadProfile();
    onSaved?.();
  };
  if (!profile) return <p className="text-sm text-stone-500">Loading profile…</p>;
  return (
    <div className="border border-stone-200 bg-white p-6 space-y-6" data-testid="owner-customer-profile">
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <ProfileStat label="Phone" value={profile.customer_phone} testid="owner-profile-phone" />
        <ProfileStat label="Visits" value={profile.visit_count} testid="owner-profile-visits" />
        <ProfileStat label="Lifetime spend" value={money(profile.lifetime_spend)} testid="owner-profile-spend" />
        <ProfileStat label="Preferred" value={`${profile.preferred_stylist_name || "—"}${profile.preferred_stylist_manual ? " · manual" : profile.preferred_stylist_name ? " · auto" : ""}`} testid="owner-profile-preferred" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <ProfileInput label="Name" value={form.customer_name} onChange={(v) => setForm({ ...form, customer_name: v })} testid="owner-profile-name" />
        <ProfileInput label="Birthday" type="date" value={form.birthday} onChange={(v) => setForm({ ...form, birthday: v })} testid="owner-profile-birthday" />
        <ProfileInput label="Hair type" value={form.hair_type} onChange={(v) => setForm({ ...form, hair_type: v })} testid="owner-profile-hair" />
        <ProfileInput label="Allergies" value={form.product_allergies} onChange={(v) => setForm({ ...form, product_allergies: v })} testid="owner-profile-allergies" />
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">Preferred stylist</p>
          <select value={form.preferred_stylist_id} onChange={(e) => setForm({ ...form, preferred_stylist_id: e.target.value })} data-testid="owner-profile-preferred-select" className="w-full border border-stone-300 px-3 py-2 bg-white">
            <option value="">Auto ({profile.preferred_stylist_name || "none"})</option>
            {stylists.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        <ProfileInput label="Preferences" value={form.preferences} onChange={(v) => setForm({ ...form, preferences: v })} testid="owner-profile-preferences" textarea />
        <ProfileInput label="Stylist notes" value={form.stylist_notes} onChange={(v) => setForm({ ...form, stylist_notes: v })} testid="owner-profile-notes" textarea />
      </div>
      <button onClick={save} data-testid="owner-profile-save" className="border border-stone-900 bg-stone-900 text-white px-4 py-2 text-xs uppercase tracking-[0.2em]">Save profile</button>
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500 mb-3">Visit history · loyalty progress {profile.loyalty_next_milestone ? `${profile.loyalty_progress}% to ${money(profile.loyalty_next_milestone)}` : "top milestone"}</p>
        <div className="space-y-2 max-h-80 overflow-auto" data-testid="owner-profile-visit-history">
          {(profile.visit_history || []).map((v) => <div key={v.id} className="grid grid-cols-1 sm:grid-cols-4 gap-2 border border-stone-100 p-3 text-sm"><span>{v.date}</span><span>{v.service_name}</span><span>{v.stylist_name}</span><span>{money(v.amount_paid)}</span></div>)}
        </div>
      </div>
    </div>
  );
}
