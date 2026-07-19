import { MapPin, Train, Users, Gauge, Activity, Navigation, GitBranch } from 'lucide-react';

const PIPELINE_STEPS = [
  { icon: MapPin, label: 'Route Simulation', desc: 'Station sequence' },
  { icon: Train, label: 'Station Arrival', desc: 'Train positioning' },
  { icon: Users, label: 'Passenger Movement', desc: 'Load change ±Δ' },
  { icon: Gauge, label: 'Coach Occupancy', desc: 'Load → %' },
  { icon: Activity, label: 'Density Analysis', desc: 'LOW → CRITICAL' },
  { icon: Navigation, label: 'Recommendation', desc: 'Best coach pick' },
  { icon: GitBranch, label: 'Crowd Optimization', desc: 'Distribution output' },
];

export default function SystemPipeline() {
  return (
    <div className="card p-5">
      <div className="section-label mb-0.5">System Process Pipeline</div>
      <div className="section-title mb-1">Software Simulation Architecture</div>
      <div className="text-[10px] text-slate-400 mb-4 font-medium">
        Software simulation architecture — hardware sensing and computer vision integration planned for future phases.
      </div>

      {/* Pipeline steps */}
      <div className="overflow-x-auto no-scrollbar">
        <div className="min-w-max flex items-center gap-0">
          {PIPELINE_STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={i} className="flex items-center">
                <div className="flex flex-col items-center px-4 py-3 group">
                  <div className="w-10 h-10 bg-blue-50 border-2 border-blue-100 group-hover:border-blue-400 group-hover:bg-blue-100 rounded-xl flex items-center justify-center mb-2 transition-all duration-150">
                    <Icon className="w-4.5 h-4.5 text-blue-600" size={18} />
                  </div>
                  <div className="text-[10px] font-bold text-slate-700 text-center whitespace-nowrap">{step.label}</div>
                  <div className="text-[9px] text-slate-400 text-center mt-0.5 whitespace-nowrap">{step.desc}</div>
                </div>

                {/* Arrow */}
                {i < PIPELINE_STEPS.length - 1 && (
                  <div className="flex items-center flex-shrink-0">
                    <div className="w-4 h-0.5 bg-slate-300"></div>
                    <div className="w-0 h-0 border-t-4 border-b-4 border-l-4 border-transparent border-l-slate-300"></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
