import { useState } from 'react';
import { getDensityConfig, formatMovement } from '../utils/densityUtils';

export default function CoachCompartment({ coach, isRecommended, stationName }) {
  const [hovered, setHovered] = useState(false);
  const cfg = getDensityConfig(coach.density_status);
  const mvt = formatMovement(coach.movement);
  const isCritical = coach.density_status === 'CRITICAL';
  const isHigh = coach.density_status === 'HIGH';

  // Window count based on coach
  const windows = [1, 2, 3, 4];

  return (
    <div
      className="relative flex flex-col flex-1 min-w-0 cursor-pointer transition-all duration-200"
      style={{ transform: hovered ? 'translateY(-3px)' : 'translateY(0)' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Recommended badge above */}
      {isRecommended && (
        <div className="absolute -top-7 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-blue-700 text-white text-[9px] font-bold tracking-widest px-2.5 py-1 rounded-full shadow-md whitespace-nowrap z-10">
          <span>★ RECOMMENDED</span>
        </div>
      )}

      {/* Coach body */}
      <div className={`flex flex-col border-2 rounded-t-xl overflow-hidden transition-all duration-200 shadow-sm ${
        isRecommended
          ? 'border-blue-500 shadow-blue-100 shadow-lg'
          : isCritical
          ? `border-red-300 ${isCritical ? 'critical-pulse' : ''}`
          : `border-slate-200`
      } bg-white`}>

        {/* Roof strip */}
        <div className={`h-2.5 ${
          isRecommended ? 'bg-blue-600' : isCritical ? 'bg-red-500' : isHigh ? 'bg-orange-500' : 'bg-slate-400'
        }`}></div>

        {/* Coach number + status */}
        <div className={`px-3 pt-2 pb-1 flex items-center justify-between ${
          isRecommended ? 'bg-blue-50' : cfg.bgColor
        }`}>
          <span className="text-[10px] font-black tracking-widest uppercase text-slate-600">
            COACH {coach.id}
          </span>
          <span className={`text-[9px] font-bold tracking-widest px-2 py-0.5 rounded-full border ${cfg.bgColor} ${cfg.borderColor} ${cfg.textColor}`}>
            {coach.density_status}
          </span>
        </div>

        {/* Windows row */}
        <div className="px-3 py-1.5 flex gap-1.5 bg-slate-50 border-y border-slate-100">
          {windows.map(w => (
            <div
              key={w}
              className="flex-1 h-6 rounded-sm border"
              style={{
                backgroundColor: isCritical ? '#fee2e2' : isHigh ? '#ffedd5' : '#e0f2fe',
                borderColor: isCritical ? '#fca5a5' : isHigh ? '#fdba74' : '#bae6fd',
              }}
            ></div>
          ))}
        </div>

        {/* Door */}
        <div className="flex justify-center py-1 bg-white">
          <div className="w-8 h-5 border-2 border-slate-300 rounded-sm bg-slate-50 flex items-center justify-center">
            <div className="w-0.5 h-3 bg-slate-300"></div>
          </div>
        </div>

        {/* Occupancy data */}
        <div className="px-3 pb-2 bg-white">
          {/* Big percentage */}
          <div className="flex items-end gap-1 mb-1">
            <span className={`text-2xl font-black leading-none ${
              isCritical ? 'text-red-600' : isHigh ? 'text-orange-600' :
              coach.density_status === 'MODERATE' ? 'text-amber-600' : 'text-emerald-600'
            }`}>
              {coach.occupancy_percentage}%
            </span>
          </div>

          {/* Occupancy bar */}
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden mb-2">
            <div
              className="h-full rounded-full transition-all duration-700 bar-animate"
              style={{
                width: `${Math.min(coach.occupancy_percentage, 100)}%`,
                backgroundColor: isCritical ? '#ef4444' : isHigh ? '#f97316' :
                  coach.density_status === 'MODERATE' ? '#f59e0b' : '#10b981',
              }}
            ></div>
          </div>

          {/* Load info */}
          <div className="flex justify-between text-[10px] text-slate-500 font-medium">
            <span>Load: <strong className="text-slate-700">{coach.current_load}</strong>/{coach.capacity}</span>
            <span>Avail: <strong className="text-emerald-600">{coach.available_capacity}</strong></span>
          </div>

          {/* Movement */}
          <div className={`mt-1.5 flex items-center gap-1 text-[11px] font-bold ${mvt.color}`}>
            <span className="text-base leading-none">{mvt.symbol}</span>
            <span>{Math.abs(coach.movement)} units</span>
          </div>
        </div>
      </div>

      {/* Undercarriage */}
      <div className="h-3 bg-slate-700 rounded-b-sm flex justify-around items-center px-3">
        <div className="w-4 h-2 rounded-full bg-slate-500 border border-slate-600"></div>
        <div className="w-4 h-2 rounded-full bg-slate-500 border border-slate-600"></div>
      </div>
      <div className="h-1 bg-slate-800 rounded-b"></div>

      {/* Hover tooltip */}
      {hovered && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-30 bg-slate-900 text-white text-[10px] rounded-lg p-3 shadow-xl w-44 pointer-events-none">
          <div className="font-bold mb-1">Coach {coach.id} — {stationName}</div>
          <div className="space-y-0.5 text-slate-300">
            <div className="flex justify-between"><span>Occupancy</span><span className="text-white font-semibold">{coach.occupancy_percentage}%</span></div>
            <div className="flex justify-between"><span>Load</span><span className="text-white font-semibold">{coach.current_load} units</span></div>
            <div className="flex justify-between"><span>Available</span><span className="text-emerald-400 font-semibold">{coach.available_capacity} units</span></div>
            <div className="flex justify-between"><span>Status</span><span className={`font-bold ${
              isCritical ? 'text-red-400' : isHigh ? 'text-orange-400' : 'text-amber-400'
            }`}>{coach.density_status}</span></div>
            <div className="flex justify-between"><span>Movement</span><span className={`font-semibold ${
              mvt.color === 'text-emerald-600' ? 'text-emerald-400' : mvt.color === 'text-blue-600' ? 'text-blue-400' : 'text-slate-400'
            }`}>{mvt.text}</span></div>
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900"></div>
        </div>
      )}
    </div>
  );
}
