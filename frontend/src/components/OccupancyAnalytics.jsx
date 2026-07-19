import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts';
import { getOccupancyBarColor } from '../utils/densityUtils';

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const d = payload[0].payload;
    return (
      <div className="bg-slate-900 text-white rounded-lg p-3 shadow-xl border border-slate-700 text-xs">
        <div className="font-bold mb-1">{d.name}</div>
        <div className="text-slate-300 space-y-0.5">
          <div>Occupancy: <span className="text-white font-semibold">{d.occupancy}%</span></div>
          <div>Available: <span className="text-emerald-400 font-semibold">{d.available} units</span></div>
          <div>Status: <span className="font-bold" style={{ color: d.statusColor }}>{d.status}</span></div>
        </div>
      </div>
    );
  }
  return null;
};

export default function OccupancyAnalytics({ coaches }) {
  const data = coaches.map(c => ({
    name: `Coach ${c.id}`,
    shortName: `C${c.id}`,
    occupancy: c.occupancy_percentage,
    available: c.available_capacity,
    status: c.density_status,
    statusColor: getOccupancyBarColor(c.occupancy_percentage),
    fill: getOccupancyBarColor(c.occupancy_percentage),
  }));

  return (
    <div className="card p-5">
      <div className="section-label mb-0.5">Coach Occupancy Analytics</div>
      <div className="section-title mb-4">Visual Load Distribution Chart</div>

      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: -10, bottom: 0 }} barCategoryGap="35%">
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 11, fontWeight: 600, fill: '#64748b' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: '#94a3b8' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `${v}%`}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f8fafc', radius: 4 }} />

          {/* Threshold reference lines */}
          <ReferenceLine y={40} stroke="#10b981" strokeDasharray="4 4" strokeWidth={1.5}
            label={{ value: 'LOW', position: 'right', fontSize: 9, fill: '#10b981', fontWeight: 700 }} />
          <ReferenceLine y={65} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth={1.5}
            label={{ value: 'MODERATE', position: 'right', fontSize: 9, fill: '#f59e0b', fontWeight: 700 }} />
          <ReferenceLine y={85} stroke="#ef4444" strokeDasharray="4 4" strokeWidth={1.5}
            label={{ value: 'CRITICAL', position: 'right', fontSize: 9, fill: '#ef4444', fontWeight: 700 }} />

          <Bar dataKey="occupancy" radius={[6, 6, 0, 0]} maxBarSize={60}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Threshold legend */}
      <div className="flex flex-wrap gap-4 mt-3 pt-3 border-t border-slate-100">
        {[
          { label: '≤ 40% — LOW', color: '#10b981' },
          { label: '≤ 65% — MODERATE', color: '#f59e0b' },
          { label: '≤ 85% — HIGH', color: '#f97316' },
          { label: '> 85% — CRITICAL', color: '#ef4444' },
        ].map((t, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <div className="w-3 h-1.5 rounded-full" style={{ backgroundColor: t.color }}></div>
            <span className="text-[10px] font-medium text-slate-500">{t.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
