import { MapPin, Gauge, BarChart2, Navigation } from 'lucide-react';
import { getDensityConfig, getAverageOccupancy, getOverallDensity } from '../utils/densityUtils';

export default function OperationalSummary({ station, coaches, recommendation }) {
  const avgOccupancy = getAverageOccupancy(coaches);
  const overallDensity = getOverallDensity(coaches);
  const densityCfg = getDensityConfig(overallDensity);

  const metrics = [
    {
      icon: MapPin,
      label: 'CURRENT STATION',
      value: station.current,
      sub: `Station ${station.index + 1} of ${station.total}`,
      valueClass: 'text-blue-700',
    },
    {
      icon: Gauge,
      label: 'OVERALL TRAIN OCCUPANCY',
      value: `${avgOccupancy}%`,
      sub: `Avg. across ${coaches.length} coaches`,
      valueClass: avgOccupancy > 85 ? 'text-red-600' : avgOccupancy > 65 ? 'text-orange-600' : avgOccupancy > 40 ? 'text-amber-600' : 'text-emerald-600',
    },
    {
      icon: BarChart2,
      label: 'NETWORK CROWD LEVEL',
      value: overallDensity,
      sub: 'Aggregated density index',
      valueClass: densityCfg.textColor,
      valueBg: densityCfg.bgColor,
      valueBorder: densityCfg.borderColor,
      isBadge: true,
    },
    {
      icon: Navigation,
      label: 'RECOMMENDED BOARDING',
      value: `COACH ${recommendation.coach_id}`,
      sub: `${recommendation.occupancy_percentage}% occupied · ${recommendation.density_status}`,
      valueClass: 'text-blue-700',
    },
  ];

  return (
    <div className="bg-white border-b border-slate-200">
      <div className="max-w-[1600px] mx-auto px-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 divide-x divide-slate-100">
          {metrics.map((m, i) => {
            const Icon = m.icon;
            return (
              <div key={i} className="py-3 px-5 flex items-center gap-3">
                <div className="flex-shrink-0 w-8 h-8 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center">
                  <Icon className="w-4 h-4 text-slate-500" />
                </div>
                <div className="min-w-0">
                  <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400 mb-0.5">{m.label}</div>
                  {m.isBadge ? (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold border ${m.valueBg} ${m.valueBorder} ${m.valueClass}`}>
                      {m.value}
                    </span>
                  ) : (
                    <div className={`text-sm font-bold truncate ${m.valueClass}`}>{m.value}</div>
                  )}
                  <div className="text-[10px] text-slate-400 truncate mt-0.5">{m.sub}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
