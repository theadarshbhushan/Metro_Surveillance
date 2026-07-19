import CoachCompartment from './CoachCompartment';
import PlatformAccess from './PlatformAccess';

// Coupling joint between two coaches
function CoachJoint() {
  return (
    <div className="flex flex-col items-center justify-center flex-shrink-0 w-4">
      <div className="w-1 h-10 bg-slate-300 rounded"></div>
      <div className="w-4 h-1.5 bg-slate-400 rounded-full -mt-1 -mb-1 z-10"></div>
      <div className="w-1 h-10 bg-slate-300 rounded"></div>
    </div>
  );
}

export default function TrainVisualization({ coaches, recommendation, station }) {
  const recommendedId = recommendation.coach_id;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="section-label mb-0.5">Live Train Occupancy</div>
          <div className="section-title">Coach-Level Crowd Distribution & Available Capacity</div>
        </div>
        <div className="text-[10px] text-slate-400 font-medium text-right">
          <div>Simulated load units per coach</div>
          <div className="text-slate-500 font-semibold">Capacity: 100 units per coach</div>
        </div>
      </div>

      {/* Train + Platform */}
      <div className="overflow-x-auto no-scrollbar">
        <div className="min-w-[720px] flex items-start gap-0 pb-4 mt-8">

          {/* Front engine cap */}
          <div className="flex-shrink-0 flex flex-col justify-end self-stretch">
            <div className="w-5 h-16 bg-gradient-to-r from-slate-600 to-slate-500 rounded-l-full mb-3 flex items-center justify-center">
              <div className="w-1 h-6 bg-slate-400 rounded-full"></div>
            </div>
            <div className="h-3 bg-slate-700 rounded-l-sm"></div>
            <div className="h-1 bg-slate-800 rounded-l"></div>
          </div>

          {/* 4 coaches */}
          {coaches.map((coach, i) => (
            <div key={coach.id} className="flex items-start flex-1 min-w-0">
              {i > 0 && <CoachJoint />}
              <CoachCompartment
                coach={coach}
                isRecommended={coach.id === recommendedId}
                stationName={station.current}
              />
            </div>
          ))}

          {/* Rear cap */}
          <div className="flex-shrink-0 flex flex-col justify-end self-stretch">
            <div className="w-5 h-16 bg-gradient-to-l from-slate-600 to-slate-500 rounded-r-full mb-3"></div>
            <div className="h-3 bg-slate-700 rounded-r-sm"></div>
            <div className="h-1 bg-slate-800 rounded-r"></div>
          </div>

          {/* Platform access section — to right of Coach 4 */}
          <div className="ml-4 self-center">
            <PlatformAccess />
          </div>
        </div>
      </div>

      {/* Track rail */}
      <div className="mt-1 mx-2">
        <div className="h-1 bg-slate-300 rounded-full w-full max-w-xl"></div>
        <div className="flex justify-between mt-0.5 max-w-xl">
          {[...Array(12)].map((_, i) => (
            <div key={i} className="w-0.5 h-2 bg-slate-300 rounded-full"></div>
          ))}
        </div>
      </div>

      {/* Density legend */}
      <div className="flex flex-wrap items-center gap-4 mt-4 pt-3 border-t border-slate-100">
        <span className="text-[9px] font-bold tracking-widest uppercase text-slate-400">Density Scale:</span>
        {[
          { label: 'LOW (0–40%)', color: 'bg-emerald-500' },
          { label: 'MODERATE (41–65%)', color: 'bg-amber-500' },
          { label: 'HIGH (66–85%)', color: 'bg-orange-500' },
          { label: 'CRITICAL (>85%)', color: 'bg-red-500' },
        ].map((d, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <div className={`w-2.5 h-2.5 rounded-sm ${d.color}`}></div>
            <span className="text-[10px] font-medium text-slate-500">{d.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
