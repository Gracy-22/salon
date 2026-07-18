import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { money, percent, PIE_COLORS, PIE_TEXT_COLORS } from "./utils";

export function ProfileStat({ label, value, testid }) {
  return (
    <div className="border border-stone-100 p-3">
      <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p>
      <p className="font-medium" data-testid={testid}>{value}</p>
    </div>
  );
}

export function ProfileInput({ label, value, onChange, testid, type = "text", textarea = false }) {
  return (
    <label className="block">
      <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-1">{label}</p>
      {textarea
        ? <textarea value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={testid} className="w-full border border-stone-300 px-3 py-2 min-h-20" />
        : <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={testid} className="w-full border border-stone-300 px-3 py-2" />}
    </label>
  );
}

export function MetricCard({ label, value, testid, icon: Icon, tone = "neutral" }) {
  return (
    <div className={`border bg-white p-5 ${tone === "danger" ? "border-rose-500" : "border-stone-200"}`} data-testid={`${testid}-card`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{label}</p>
        {Icon && <Icon className="h-4 w-4 text-stone-400" />}
      </div>
      <p className={`font-serif text-3xl mt-3 ${tone === "danger" ? "text-rose-700" : "text-stone-900"}`} data-testid={testid}>{value}</p>
    </div>
  );
}

export function RankedList({ icon: Icon, title, rows, testid }) {
  return (
    <section className="border border-stone-200 bg-white p-6" data-testid={testid}>
      <div className="flex items-center gap-2 mb-4">
        <Icon className="h-4 w-4 text-stone-400" />
        <p className="text-xs uppercase tracking-[0.25em] text-stone-500">{title}</p>
      </div>
      {rows.length === 0
        ? <p className="text-sm text-stone-500" data-testid={`${testid}-empty`}>No revenue yet.</p>
        : <RevenuePieChart rows={rows} testid={`${testid}-pie`} showCount={testid.includes("service")} />}
    </section>
  );
}

export function RevenuePieChart({ rows, testid, showCount = false }) {
  const chartRows = rows.filter((row) => Number(row.revenue || 0) > 0);
  const totalRevenue = chartRows.reduce((sum, row) => sum + Number(row.revenue || 0), 0);
  if (chartRows.length === 0) return null;

  const labelText = (entry) => `${entry.name}${showCount ? ` · ${entry.count}` : ""} (${percent(entry.revenue, totalRevenue)})`;
  const renderLabel = ({ cx, cy, midAngle, outerRadius, index }) => {
    const RADIAN = Math.PI / 180;
    const radius = outerRadius + 38;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);
    const color = PIE_TEXT_COLORS[index % PIE_TEXT_COLORS.length];
    return (
      <text x={x} y={y} fill={color} textAnchor={x > cx ? "start" : "end"} dominantBaseline="central" fontSize={12} fontWeight={600}>
        {labelText(chartRows[index])}
      </text>
    );
  };
  const renderLabelLine = ({ points, index }) => (
    <polyline points={points.map((point) => `${point.x},${point.y}`).join(" ")} fill="none" stroke={PIE_TEXT_COLORS[index % PIE_TEXT_COLORS.length]} strokeWidth={1.6} />
  );

  return (
    <div className="min-w-0" data-testid={testid}>
      <div className="h-[26rem]" data-testid={`${testid}-chart`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart margin={{ top: 34, right: 96, bottom: 34, left: 96 }}>
            <Pie data={chartRows} dataKey="revenue" nameKey="name" innerRadius="42%" outerRadius="76%" paddingAngle={2} stroke="#ffffff" strokeWidth={2} label={renderLabel} labelLine={renderLabelLine}>
              {chartRows.map((row, index) => (
                <Cell key={row.id} fill={PIE_COLORS[index % PIE_COLORS.length]} data-testid={`${testid}-slice-${row.id}`} />
              ))}
            </Pie>
            <Tooltip formatter={(value, name) => [money(value), name]} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
