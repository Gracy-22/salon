import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { format } from "date-fns";
import { toast } from "sonner";
import { LogOut, Calendar as CalendarIcon, Menu, X, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import { API, ownerAuthConfig, to12h, STATUS_LABELS, ALL_SALONS } from "./owner/utils";
import { OwnerSideMenu } from "./owner/OwnerSideMenu";
import { DailyBook } from "./owner/DailyBook";
import { NoShowTracker } from "./owner/NoShowTracker";
import { InsightsDashboard } from "./owner/InsightsDashboard";
import { OwnerCustomerDirectory } from "./owner/OwnerCustomerDirectory";
import { StaffTreatmentsManager } from "./owner/StaffTreatmentsManager";
import { SalonsManager } from "./owner/SalonsManager";
import { getValidToken } from "../lib/authStore";

const HIDE_CALENDAR_TABS = new Set(["insights", "customers", "staff", "salons"]);

export default function OwnerDashboard() {
  const navigate = useNavigate();
  const [date, setDate] = useState(new Date());
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [tab, setTab] = useState("daily");
  const [salons, setSalons] = useState([]);
  const [salonId, setSalonId] = useState(ALL_SALONS);

  const ownerToken = getValidToken("owner");

  const [notifications, setNotifications] = useState({ unread: 0, notifications: [] });
  const loadNotifications = useCallback(() => {
    if (!ownerToken) return;
    axios.get(`${API}/owner/notifications`, ownerAuthConfig(ownerToken)).then((r) => setNotifications(r.data)).catch(() => {});
  }, [ownerToken]);

  const loadSalons = useCallback(() => {
    if (!ownerToken) return;
    axios.get(`${API}/owner/salons`, ownerAuthConfig(ownerToken)).then((r) => setSalons(r.data.salons || [])).catch(() => {});
  }, [ownerToken]);

  useEffect(() => { if (!ownerToken) navigate("/owner", { replace: true }); }, [ownerToken, navigate]);
  useEffect(() => { loadSalons(); }, [loadSalons]);

  const dateStr = format(date, "yyyy-MM-dd");
  const salonParam = salonId === ALL_SALONS ? undefined : salonId;
  const handleAuthError = useCallback((error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem("owner_token");
      toast.error("Owner session expired. Please sign in again.");
      navigate("/owner", { replace: true });
      return true;
    }
    return false;
  }, [navigate]);

  const load = useCallback(() => {
    if (!ownerToken) return;
    setLoading(true);
    const params = { date: dateStr };
    if (salonParam) params.salon_id = salonParam;
    axios.get(`${API}/owner/bookings`, { params, ...ownerAuthConfig(ownerToken) })
      .then((b) => { setBookings(b.data.bookings); })
      .catch((error) => { if (!handleAuthError(error)) toast.error("Could not load"); })
      .finally(() => setLoading(false));
  }, [ownerToken, dateStr, salonParam, handleAuthError]);

  useEffect(() => { if (ownerToken) load(); }, [load, ownerToken]);

  const cancel = async (b) => {
    if (!window.confirm(`Cancel ${b.customer_name}'s ${to12h(b.start_time)} booking?`)) return;
    try {
      await axios.patch(`${API}/owner/bookings/${b.id}/cancel`, null, ownerAuthConfig(ownerToken));
      toast.success("Booking cancelled");
      load();
    } catch (error) { if (!handleAuthError(error)) toast.error("Cancel failed"); }
  };

  const setStatus = async (b, status) => {
    try {
      await axios.patch(`${API}/owner/bookings/${b.id}/status`, { status }, ownerAuthConfig(ownerToken));
      toast.success(status === "no_show" ? "Marked no-show and sent follow-up if available" : `Marked ${STATUS_LABELS[status]}`);
      load();
    } catch (error) { if (!handleAuthError(error)) toast.error("Status update failed"); }
  };

  const logout = () => { localStorage.removeItem("owner_token"); navigate("/owner", { replace: true }); };

  useEffect(() => { loadNotifications(); }, [loadNotifications]);

  if (!ownerToken) return null;

  const hideCalendar = HIDE_CALENDAR_TABS.has(tab);
  const activeSalons = salons.filter((s) => s.is_active !== false);

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-[#FAF9F6]">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button onClick={() => setMobileMenuOpen(true)} data-testid="owner-mobile-menu-open" className="lg:hidden border border-stone-300 p-2 hover:border-stone-900"><Menu className="h-4 w-4" /></button>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-stone-500">The Gentlemen&apos;s Room</p>
              <h1 className="font-serif text-2xl mt-1">Owner Dashboard</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {activeSalons.length > 0 && (
              <select
                value={salonId}
                onChange={(e) => setSalonId(e.target.value)}
                data-testid="owner-salon-switcher"
                className="h-9 rounded-none border border-stone-300 bg-white px-3 text-xs uppercase tracking-[0.15em] text-stone-700 focus:outline-none focus:border-stone-900"
                title="Filter dashboard by salon"
              >
                <option value={ALL_SALONS}>All salons</option>
                {activeSalons.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            )}
            {notifications.unread > 0 && <span data-testid="owner-notification-badge" className="text-xs uppercase tracking-[0.18em] text-rose-700">{notifications.unread} new</span>}
            <button onClick={logout} data-testid="btn-owner-logout" className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-stone-600 hover:text-stone-900">
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="py-0">
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 lg:hidden" data-testid="owner-mobile-sidebar">
            <button className="absolute inset-0 bg-stone-950/30" onClick={() => setMobileMenuOpen(false)} aria-label="Close owner menu" />
            <aside className="relative h-full w-80 max-w-[85vw] bg-[#FAF9F6] border-r border-stone-200 p-4 shadow-xl">
              <div className="flex items-center justify-between mb-6">
                <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Menu</p>
                <button onClick={() => setMobileMenuOpen(false)} data-testid="owner-mobile-menu-close" className="border border-stone-300 p-2"><X className="h-4 w-4" /></button>
              </div>
              <OwnerSideMenu tab={tab} setTab={(key) => { setTab(key); setMobileMenuOpen(false); }} collapsed={false} />
            </aside>
          </div>
        )}

        <div className={`grid grid-cols-1 lg:grid-cols-[auto_minmax(0,1fr)] ${sidebarCollapsed ? "lg:gap-6" : "lg:gap-8"}`}>
          <aside className={`hidden lg:block shrink-0 min-h-[calc(100vh-97px)] border-r border-stone-200 bg-white transition-all duration-300 ${sidebarCollapsed ? "w-20" : "w-72"}`} data-testid="owner-sidebar">
            <div className="sticky top-0 p-3">
              <div className="flex items-center justify-between gap-2 mb-4 px-2">
                {!sidebarCollapsed && <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Owner menu</p>}
                <button onClick={() => setSidebarCollapsed((v) => !v)} data-testid="owner-sidebar-toggle" className="border border-stone-300 p-2 hover:border-stone-900 ml-auto" aria-label="Toggle owner sidebar">
                  {sidebarCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
                </button>
              </div>
              <OwnerSideMenu tab={tab} setTab={setTab} collapsed={sidebarCollapsed} />
            </div>
          </aside>

          <div className={`py-10 px-6 lg:pl-0 lg:pr-8 min-w-0 ${hideCalendar ? "block" : "grid grid-cols-1 xl:grid-cols-[300px_1fr] gap-10"}`}>
            {!hideCalendar && (
              <aside>
                <div className="flex items-center gap-2 mb-3"><CalendarIcon className="h-4 w-4 text-stone-500" /><p className="text-xs uppercase tracking-[0.25em] text-stone-500">Day</p></div>
                <div className="border border-stone-200 bg-white p-3">
                  <Calendar mode="single" selected={date} onSelect={(d) => d && setDate(d)} className="rounded-none" />
                </div>
              </aside>
            )}

            <section>
              {tab === "daily" && <DailyBook ownerToken={ownerToken} date={date} setDate={setDate} bookings={bookings} loading={loading} onCancel={cancel} onSetStatus={setStatus} salonId={salonParam} />}
              {tab === "noshow" && <NoShowTracker ownerToken={ownerToken} salonId={salonParam} />}
              {tab === "customers" && <OwnerCustomerDirectory ownerToken={ownerToken} />}
              {tab === "staff" && <StaffTreatmentsManager ownerToken={ownerToken} salons={salons} salonFilter={salonParam} />}
              {tab === "salons" && <SalonsManager ownerToken={ownerToken} onSalonsChanged={loadSalons} />}
              {tab === "insights" && <InsightsDashboard ownerToken={ownerToken} salonId={salonParam} />}
            </section>
          </div>
        </div>
      </main>
    </div>
  );
}
