import { TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

export default function DistributionInsight({ coaches }) {
  if (!coaches || coaches.length === 0) return null;

  const sorted = [...coaches].sort((a, b) => b.occupancy_percentage - a.occupancy_percentage);
  const mostCrowded = sorted[0];
  const leastCrowded = sorted[sorted.length - 1];
  const diff = Math.round((mostCrowded.occupancy_percentage - leastCrowded.occupancy_percentage) * 10) / 10;
  const imbalanceDetected = diff > 25;

  return (
    <div className="card p-5">
      <div className="section-label mb-0.5">Crowd Distribution Insight</div>
      <div className="section-title mb-4">Load Imbalance Analysis</div>

      <div className="space-y-3">
        {/* Most crowded */}
        <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-100 rounded-lg">
          <div className="w-8 h-8 bg-red-100 border border-red-200 rounded-lg flex items-center justify-center flex-shrink-0">
            <TrendingUp className="w-4 h-4 text-red-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[9px] font-bold tracking-widest uppercase text-red-500">Most Crowded</div>
            <div className="text-sm font-bold text-slate-800">Coach {mostCrowded.id}</div>
          </div>
          <div className="text-right">
            <div className="text-xl font-black text-red-600">{mostCrowded.occupancy_percentage}%</div>
            <div className="text-[9px] text-red-500 font-semibold">{mostCrowded.density_status}</div>
          </div>
        </div>

        {/* Least crowded */}
        <div className="flex items-center gap-3 p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
          <div className="w-8 h-8 bg-emerald-100 border border-emerald-200 rounded-lg flex items-center justify-center flex-shrink-0">
            <TrendingDown className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[9px] font-bold tracking-widest uppercase text-emerald-500">Least Crowded</div>
            <div className="text-sm font-bold text-slate-800">Coach {leastCrowded.id}</div>
          </div>
          <div className="text-right">
            <div className="text-xl font-black text-emerald-600">{leastCrowded.occupancy_percentage}%</div>
            <div className="text-[9px] text-emerald-500 font-semibold">{leastCrowded.density_status}</div>
          </div>
        </div>

        {/* Imbalance gap */}
        <div className="p-3 bg-slate-50 border border-slate-100 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[9px] font-bold tracking-widest uppercase text-slate-400">Occupancy Difference</span>
            <span className="text-xl font-black text-slate-700">{diff}%</span>
          </div>
          {/* Visual gap bar */}
          <div className="relative h-2 bg-slate-200 rounded-full overflow-hidden">
            <div className="absolute left-0 h-full bg-emerald-400 rounded-full"
              style={{ width: `${leastCrowded.occupancy_percentage}%` }}></div>
            <div className="absolute right-0 h-full bg-red-400 rounded-full"
              style={{ width: `${100 - mostCrowded.occupancy_percentage}%` }}></div>
          </div>
        </div>

        {/* Imbalance alert */}
        {imbalanceDetected && (
          <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <div>
              <div className="text-[9px] font-black tracking-widest uppercase text-amber-700">Distribution Imbalance Detected</div>
              <div className="text-[10px] text-amber-600 mt-0.5">
                {diff}% gap between coaches. Recommendation engine activated.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
