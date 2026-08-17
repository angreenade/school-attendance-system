import { useEffect, useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { api } from "../../api/client";
import type { LocationOut, SummaryStats } from "../../api/types";

const RANGE_PRESETS = [
  { label: "Last 7 days", days: 7 },
  { label: "Last 30 days", days: 30 },
  { label: "Winter term (last 60 days)", days: 60 },
];

function isoDaysAgo(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function Overview() {
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [locations, setLocations] = useState<LocationOut[]>([]);
  const [rangeDays, setRangeDays] = useState(30);
  const [locationId, setLocationId] = useState<string>("");

  useEffect(() => {
    api.get("/api/locations").then((res) => setLocations(res.data));
  }, []);

  useEffect(() => {
    const params: Record<string, string> = { date_from: isoDaysAgo(rangeDays) };
    if (locationId) params.location_id = locationId;
    api.get("/api/attendance/stats/summary", { params }).then((res) => setStats(res.data));
  }, [rangeDays, locationId]);

  const chartData = useMemo(
    () =>
      (stats?.daily || []).map((d) => ({
        date: new Date(d.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        "On time": d.on_time,
        Late: d.late,
      })),
    [stats]
  );

  return (
    <div className="page">
      <div className="page-header">
        <h1>Overview</h1>
        <div className="filter-row">
          <select value={rangeDays} onChange={(e) => setRangeDays(Number(e.target.value))}>
            {RANGE_PRESETS.map((p) => (
              <option key={p.days} value={p.days}>{p.label}</option>
            ))}
          </select>
          <select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
            <option value="">All locations</option>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>{l.name}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="stat-tiles">
        <div className="stat-tile">
          <span className="stat-label">Total scans</span>
          <span className="stat-value">{stats?.total_scans ?? "–"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Unique students seen</span>
          <span className="stat-value">{stats?.unique_students ?? "–"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">On-time rate</span>
          <span className="stat-value status-good">{stats ? `${Math.round(stats.on_time_rate * 100)}%` : "–"}</span>
        </div>
        <div className="stat-tile">
          <span className="stat-label">Late rate</span>
          <span className="stat-value status-warning">{stats ? `${Math.round(stats.late_rate * 100)}%` : "–"}</span>
        </div>
      </div>

      <div className="chart-card">
        <h2>Daily attendance &mdash; on-time vs. late</h2>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={chartData} barGap={2} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="#e1e0d9" />
            <XAxis dataKey="date" tick={{ fill: "#898781", fontSize: 12 }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
            <YAxis allowDecimals={false} tick={{ fill: "#898781", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "#fcfcfb", border: "1px solid #e1e0d9", borderRadius: 8, fontSize: 13 }}
              cursor={{ fill: "rgba(11,11,11,0.04)" }}
            />
            <Legend wrapperStyle={{ fontSize: 13, color: "#52514e" }} />
            <Bar dataKey="On time" stackId="a" fill="#0ca30c" radius={[0, 0, 0, 0]} maxBarSize={24} />
            <Bar dataKey="Late" stackId="a" fill="#fab219" radius={[4, 4, 0, 0]} maxBarSize={24} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
