import { Navigation, ArrowRight, Cpu } from 'lucide-react';
import { getDensityConfig } from '../utils/densityUtils';

export default function RecommendationPanel({ recommendation, coaches }) {
  const cfg = getDensityConfig(recommendation.density_status);
  const mostCrowded = [...coaches].sort((a, b) => b.occupancy_percentage - a.occupancy_percentage)[0];

  return (
    <div className="card p-5 border-l-4 border-l-blue-600">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="section-label mb-0.5">Smart Crowd Recommendation</div>
          <div className="section-title">Optimal Boarding Coach Selection</div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 border border-slate-200 rounded-full">
          <Cpu className="w-3 h-3 text-slate-500" />
          <span className="text-[9px] font-bold tracking-widest uppercase text-slate-500">Rule-Based Decision Engine</span>
        </div>
      </div>

      {/* Main recommendation */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4">
        <div className="text-[9px] font-bold tracking-widest uppercase text-blue-500 mb-1">Best Boarding Option</div>
        <div className="flex items-end gap-3 mb-3">
          <div className="text-4xl font-black text-blue-700">
            COACH {recommendation.coach_id}
          </div>
          <Navigation className="w-7 h-7 text-blue-500 mb-1 arrow-pulse" />
        </div>

        <div className="grid grid-cols-3 gap-3 mb-3">
          <div className="bg-white rounded-lg p-2.5 border border-blue-100 text-center">
            <div className="text-xl font-black text-blue-700">{recommendation.occupancy_percentage}%</div>
            <div className="text-[9px] font-semibold text-slate-500 mt-0.5">Occupancy</div>
          </div>
          <div className="bg-white rounded-lg p-2.5 border border-blue-100 text-center">
            <div className="text-xl font-black text-emerald-600">{recommendation.available_capacity}</div>
            <div className="text-[9px] font-semibold text-slate-500 mt-0.5">Units Available</div>
          </div>
          <div className="bg-white rounded-lg p-2.5 border border-blue-100 text-center">
            <span className={`text-sm font-black ${cfg.textColor}`}>{recommendation.density_status}</span>
            <div className="text-[9px] font-semibold text-slate-500 mt-0.5">Crowd Level</div>
          </div>
        </div>

        {/* Instruction */}
        <div className="flex items-center gap-2 bg-blue-700 text-white rounded-lg px-3 py-2">
          <ArrowRight className="w-4 h-4 flex-shrink-0" />
          <span className="text-xs font-bold tracking-wide">
            PROCEED TOWARDS COACH {recommendation.coach_id}
          </span>
        </div>
      </div>

      {/* Directional flow */}
      <div className="flex items-center gap-3 mb-4 bg-slate-50 rounded-lg p-3 border border-slate-100">
        <div className="text-center">
          <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400 mb-1">High Density</div>
          <div className="px-2.5 py-1 bg-red-100 border border-red-200 rounded-lg text-xs font-bold text-red-600">
            Coach {mostCrowded.id}
          </div>
          <div className="text-[9px] text-red-500 mt-0.5">{mostCrowded.occupancy_percentage}%</div>
        </div>
        <div className="flex-1 flex items-center gap-1">
          <div className="flex-1 h-0.5 bg-slate-300 rounded"></div>
          <ArrowRight className="w-4 h-4 text-blue-500 flex-shrink-0 arrow-pulse" />
          <div className="flex-1 h-0.5 bg-blue-300 rounded"></div>
        </div>
        <div className="text-center">
          <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400 mb-1">Recommended</div>
          <div className="px-2.5 py-1 bg-blue-100 border border-blue-300 rounded-lg text-xs font-bold text-blue-700">
            Coach {recommendation.coach_id}
          </div>
          <div className="text-[9px] text-blue-500 mt-0.5">{recommendation.occupancy_percentage}%</div>
        </div>
      </div>

      {/* Reason */}
      <div className="bg-slate-50 border border-slate-100 rounded-lg p-3">
        <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400 mb-1">System Reasoning</div>
        <p className="text-xs text-slate-600 leading-relaxed">{recommendation.reason}</p>
      </div>
    </div>
  );
}
