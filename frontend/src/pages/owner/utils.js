import { format } from "date-fns";
import { Calendar as CalendarIcon, BarChart3, Ban, Users, Scissors, Building2 } from "lucide-react";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const ownerAuthConfig = (token) => ({ headers: { Authorization: `Bearer ${token}` } });

export const ALL_SALONS = "__all__";

export const to12h = (t) => {
  if (!t || typeof t !== "string") return t || "";
  const [h, m] = t.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, "0")} ${ampm}`;
};

export const money = (value) => `₹${Math.round(Number(value || 0)).toLocaleString("en-IN")}`;

export const formatShortDate = (dateStr) => dateStr ? format(new Date(`${dateStr}T00:00:00`), "d MMM yyyy") : "";

export const formatRangeDisplay = (range) => {
  if (!range?.start_date || !range?.end_date) return "";
  if (range.start_date === range.end_date) return formatShortDate(range.start_date);
  return `${formatShortDate(range.start_date)} - ${formatShortDate(range.end_date)}`;
};

export const percent = (value, total) => {
  if (!total) return "0%";
  const raw = (Number(value || 0) / total) * 100;
  return `${raw % 1 === 0 ? raw.toFixed(0) : raw.toFixed(1)}%`;
};

export const STATUS_STYLES = {
  upcoming: "bg-stone-100 text-stone-700 border-stone-300",
  done: "bg-emerald-100 text-emerald-900 border-emerald-400",
  no_show: "bg-rose-100 text-rose-900 border-rose-400",
  cancelled: "bg-stone-100 text-stone-400 border-stone-300 line-through",
};

export const STATUS_LABELS = { upcoming: "Upcoming", done: "Done", no_show: "No-show", cancelled: "Cancelled" };

export const TABS = [
  { key: "daily", label: "Daily Book", description: "Appointments", icon: CalendarIcon },
  { key: "customers", label: "Customer Tracker", description: "History", icon: Users },
  { key: "staff", label: "Staff & Treatments", description: "Team setup", icon: Scissors },
  { key: "salons", label: "Salons", description: "Locations", icon: Building2 },
  { key: "noshow", label: "No Show Tracker", description: "Missed visits", icon: Ban },
  { key: "insights", label: "Insights", description: "Revenue", icon: BarChart3 },
];

export const PERIOD_OPTIONS = [
  { value: "day", label: "Daily" },
  { value: "week", label: "Weekly" },
  { value: "month", label: "Monthly" },
  { value: "custom", label: "Custom Range" },
];

export const PERIOD_KPI_LABELS = { day: "Selected day", week: "Selected week", month: "Selected month", custom: "Selected range" };

export const PIE_COLORS = ["#F8B4C4", "#B8E0D2", "#A7C7E7", "#F9DCC4", "#D8B4F8", "#FFE5A3", "#C7F9CC", "#FBCFE8"];
export const PIE_TEXT_COLORS = ["#BE4563", "#2F7D6B", "#2F6FA5", "#B86D35", "#7C3FB0", "#B98700", "#2F8A43", "#B33B73"];
