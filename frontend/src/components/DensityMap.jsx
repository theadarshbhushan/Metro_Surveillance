import { getDensityConfig } from '../utils/densityUtils';

export default function DensityMap({ coaches }) {
  return (
    <div className="card p-5">
      <div className="section-label mb-0.5">Train Density Map</div>
      <div className="section-title mb-4">Coach-Level Heat Overview</div>

      <div className="grid grid-cols-4 gap-2">
        {coaches.map(coach => {
          const cfg = getDensityConfig(coach.density_status);
          const isCritical = coach.density_status === 'CRITICAL';
          return (
            <div
              key={coach.id}
              className={`rounded-xl border-2 p-3 flex flex-col items-center gap-2 transition-all duration-300 ${cfg.bgColor} ${cfg.borderColor}`}
            >
              {/* Coach label */}
              <div className="text-[9px] font-black tracking-widest uppercase text-slate-500">C{coach.id}</div>

              {/* Heat block */}
              <div
                className={`w-full h-10 rounded-lg flex items-center justify-center ${isCritical ? 'critical-pulse' : ''}`}
                style={{ backgroundColor: cfg.hex, opacity: 0.85 }}
              >
                <span className="text-sm font-black text-white drop-shadow-sm">
                  {coach.occupancy_percentage}%
                </span>
              </div>

              {/* Status badge */}
              <span className={`text-[8px] font-black tracking-widest text-center ${cfg.textColor}`}>
                {coach.density_status}
              </span>

              {/* Thin occupancy bar */}
              <div className="w-full h-1 bg-white bg-opacity-60 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${coach.occupancy_percentage}%`,
                    backgroundColor: cfg.hex,
                  }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 text-[9px] text-slate-400 text-center font-medium">
        Density blocks mirror the physical train order. Coach 4 is nearest platform access.
      </div>
    </div>
  );
}
