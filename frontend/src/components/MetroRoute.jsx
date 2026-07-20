import { Train } from 'lucide-react';

function buildRouteStations(station) {
  return Array.from({ length: station.total }, (_, i) => {
    let name = `Station ${i + 1}`;

    if (i === station.index - 1 && station.previous) name = station.previous;
    if (i === station.index) name = station.current;
    if (i === station.index + 1 && station.next) name = station.next;

    return { name };
  });
}

export default function MetroRoute({ station }) {
  const { index } = station;
  const routeStations = buildRouteStations(station);

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="section-label mb-0.5">Live Metro Route</div>
          <div className="section-title">Train Progression Across Simulated Stations</div>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-semibold text-slate-400">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-600 inline-block"></span>Completed</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full border-2 border-blue-600 inline-block"></span>Current</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full border-2 border-slate-300 inline-block"></span>Upcoming</span>
        </div>
      </div>

      <div className="overflow-x-auto no-scrollbar">
        <div className="min-w-max px-2 pb-2">
          <div className="relative flex items-center justify-between gap-0">
            {routeStations.map((s, i) => {
              const isCompleted = i < index;
              const isCurrent = i === index;

              return (
                <div key={i} className="flex items-center">
                  <div className="flex flex-col items-center relative">
                    {isCurrent && (
                      <div className="absolute -top-5 left-1/2 -translate-x-1/2 bg-blue-700 text-white text-[8px] font-bold tracking-widest px-1.5 py-0.5 rounded-full uppercase whitespace-nowrap">
                        CURRENT
                      </div>
                    )}

                    <div className="relative flex items-center justify-center">
                      {isCurrent && (
                        <span className="absolute w-6 h-6 rounded-full bg-blue-400 opacity-40 station-pulse"></span>
                      )}
                      <div className={`relative z-10 rounded-full border-2 flex items-center justify-center transition-all duration-300 ${
                        isCompleted
                          ? 'w-4 h-4 bg-blue-700 border-blue-700'
                          : isCurrent
                          ? 'w-5 h-5 bg-blue-700 border-blue-700 ring-4 ring-blue-100'
                          : 'w-4 h-4 bg-white border-slate-300'
                      }`}>
                        {isCompleted && <div className="w-1.5 h-1.5 rounded-full bg-white"></div>}
                        {isCurrent && <div className="w-2 h-2 rounded-full bg-white"></div>}
                      </div>
                    </div>

                    {isCurrent ? (
                      <div className="mt-1">
                        <Train className="w-3.5 h-3.5 text-blue-700" strokeWidth={2.5} />
                      </div>
                    ) : (
                      <div className="mt-1 h-3.5"></div>
                    )}

                    <div className={`mt-1 text-[10px] font-semibold text-center whitespace-nowrap ${
                      isCurrent ? 'text-blue-700' : isCompleted ? 'text-slate-500' : 'text-slate-300'
                    }`}>
                      {s.name}
                    </div>
                    <div className={`text-[9px] font-medium ${isCurrent ? 'text-blue-500' : 'text-slate-300'}`}>
                      {i + 1}
                    </div>
                  </div>

                  {i < routeStations.length - 1 && (
                    <div className={`h-0.5 flex-1 mx-1 w-14 rounded-full transition-colors duration-300 ${
                      i < index ? 'bg-blue-700' : 'bg-slate-200'
                    }`}></div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-6 mt-3 pt-3 border-t border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-bold tracking-widest uppercase text-slate-400">Previous</span>
          <span className="text-xs font-semibold text-slate-500">{station.previous || '-'}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-bold tracking-widest uppercase text-blue-500">Current</span>
          <span className="text-xs font-bold text-blue-700">{station.current}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-bold tracking-widest uppercase text-slate-400">Next</span>
          <span className="text-xs font-semibold text-slate-500">{station.next || '-'}</span>
        </div>
        {station.at_final_station && (
          <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-[10px] font-bold rounded-full border border-slate-200">
            SIMULATION COMPLETE
          </span>
        )}
      </div>
    </div>
  );
}
