import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { API, ownerAuthConfig, money } from "./utils";

export function SalonMenuManager({ ownerToken, salons = [], selectedSalonId, onSelectSalonId }) {
  const activeSalons = salons.filter((s) => s.is_active !== false);
  const salonId = selectedSalonId || activeSalons[0]?.id || "salon-main";
  const [menu, setMenu] = useState([]);
  const [draft, setDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    if (!ownerToken || !salonId) return;
    setLoading(true);
    axios.get(`${API}/owner/salons/${salonId}/menu`, ownerAuthConfig(ownerToken))
      .then((r) => {
        setMenu(r.data.menu || []);
        const d = {};
        (r.data.menu || []).forEach((row) => { d[row.id] = { is_offered: row.is_offered, price_override: row.price_override ?? "" }; });
        setDraft(d);
      })
      .catch(() => toast.error("Could not load salon menu"))
      .finally(() => setLoading(false));
  }, [ownerToken, salonId]);
  useEffect(() => { load(); }, [load]);

  const dirty = useMemo(() => {
    if (menu.length === 0) return false;
    return menu.some((row) => {
      const d = draft[row.id] || {};
      const priceEq = String(d.price_override ?? "") === String(row.price_override ?? "");
      return d.is_offered !== row.is_offered || !priceEq;
    });
  }, [menu, draft]);

  const save = async () => {
    const entries = Object.entries(draft).map(([service_id, v]) => ({
      service_id,
      is_offered: !!v.is_offered,
      price_override: v.price_override === "" || v.price_override === null ? null : Number(v.price_override),
    }));
    setSaving(true);
    try {
      await axios.put(`${API}/owner/salons/${salonId}/menu`, { entries }, ownerAuthConfig(ownerToken));
      toast.success("Salon menu updated");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (activeSalons.length === 0) return null;
  const activeCount = menu.filter((row) => (draft[row.id]?.is_offered ?? row.is_offered)).length;

  return (
    <section className="border border-stone-200 bg-white p-6 2xl:col-span-2" data-testid="owner-salon-menu">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Salon menu</p>
          <p className="text-sm text-stone-500 mt-1">Toggle which treatments each location offers and set optional per-location prices.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs uppercase tracking-[0.2em] text-stone-400">Location</label>
          <select
            value={salonId}
            onChange={(e) => onSelectSalonId?.(e.target.value)}
            data-testid="salon-menu-salon-select"
            className="h-9 rounded-none border border-stone-300 bg-white px-3 text-xs uppercase tracking-[0.15em] text-stone-700 focus:outline-none focus:border-stone-900"
          >
            {activeSalons.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      </div>

      {loading ? <p className="text-sm text-stone-500" data-testid="salon-menu-loading">Loading…</p> : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-[36rem] overflow-auto" data-testid="salon-menu-list">
            <div className="hidden md:flex col-span-full items-center justify-between px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-stone-400 border-b border-stone-100 sticky top-0 bg-white">
              <span>Treatment</span>
              <span>Price override (₹)</span>
            </div>
            {menu.map((row) => {
              const d = draft[row.id] || { is_offered: true, price_override: "" };
              return (
                <div key={row.id} className={`border p-3 flex items-start justify-between gap-3 ${d.is_offered ? "border-stone-200" : "border-stone-100 bg-stone-50 opacity-70"}`} data-testid={`salon-menu-row-${row.id}`}>
                  <label className="flex items-start gap-2 min-w-0 flex-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!d.is_offered}
                      onChange={(e) => setDraft({ ...draft, [row.id]: { ...d, is_offered: e.target.checked } })}
                      data-testid={`salon-menu-offered-${row.id}`}
                      className="mt-1"
                    />
                    <div className="min-w-0">
                      <p className="font-serif text-lg truncate">{row.name}</p>
                      <p className="text-xs text-stone-500">{row.category} · base {money(row.price)} · {row.duration_min}m</p>
                    </div>
                  </label>
                  <input
                    type="number"
                    value={d.price_override ?? ""}
                    onChange={(e) => setDraft({ ...draft, [row.id]: { ...d, price_override: e.target.value } })}
                    placeholder={String(row.price)}
                    disabled={!d.is_offered}
                    data-testid={`salon-menu-price-${row.id}`}
                    className="w-24 border border-stone-300 px-2 py-1 text-right text-sm disabled:bg-stone-50 disabled:opacity-60"
                  />
                </div>
              );
            })}
          </div>
          <div className="flex items-center justify-between mt-5">
            <p className="text-xs text-stone-500" data-testid="salon-menu-active-count">{activeCount} of {menu.length} treatments offered</p>
            <button onClick={save} disabled={!dirty || saving} data-testid="salon-menu-save-button" className="bg-stone-900 text-white px-4 py-3 text-xs uppercase tracking-[0.2em] disabled:opacity-40 disabled:cursor-not-allowed">
              {saving ? "Saving…" : "Save menu"}
            </button>
          </div>
        </>
      )}
    </section>
  );
}
