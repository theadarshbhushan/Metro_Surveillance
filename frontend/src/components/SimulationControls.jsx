import { ChevronRight, RotateCcw, MapPin, Flag } from 'lucide-react';

export default function SimulationControls({ station, onNext, onReset, disabled }) {
  const { current, next, index, total, at_final_station } = station;
  const progressPct = Math.round(((index + 1) / total) * 100);
  const routePositions = Array.from({ length: total }, (_, i) => i);
  const controlsDisabled = disabled || at_final_station;

  return (
    <div className="card p-5 border-2 border-slate-200">
      <div className="section-label mb-0.5">Simulation Control Center</div>
      <div className="section-title mb-4">Station Navigation & Simulation Management</div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <MapPin className="w-3.5 h-3.5 text-blue-600" />
            <span className="text-[9px] font-bold tracking-widest uppercase text-slate-400">Current Station</span>
          </div>
          <div className="text-lg font-black text-blue-700">{current}</div>
          <div className="text-[10px] text-slate-400 mt-1 font-medium">Station {index + 1} of {total}</div>
        </div>

        <div className={`border rounded-xl p-4 ${at_final_station ? 'bg-slate-100 border-slate-300' : 'bg-slate-50 border-slate-200'}`}>
          <div className="flex items-center gap-2 mb-1">
            <Flag className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-[9px] font-bold tracking-widest uppercase text-slate-400">Next Station</span>
          </div>
          {at_final_station ? (
            <div className="text-sm font-bold text-slate-400 italic">Simulation Complete</div>
          ) : (
            <div className="text-lg font-black text-slate-700">{next || '-'}</div>
          )}
          {at_final_station && (
            <div className="text-[10px] text-slate-400 mt-1">Reset to replay the route</div>
          )}
        </div>
      </div>

      <div className="mb-4">
        <div className="flex justify-between items-center mb-1.5">
          <span className="text-[10px] font-bold text-slate-500">Route Progress</span>
          <span className="text-[10px] font-bold text-slate-600">{index + 1} / {total} Stations</span>
        </div>
        <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
          <div
            className="h-full bg-blue-600 rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          ></div>
        </div>

        <div className="flex justify-between mt-1">
          {routePositions.map(i => (
            <div
              key={i}
              className={`w-1 h-1 rounded-full ${i <= index ? 'bg-blue-600' : 'bg-slate-300'}`}
              title={`Station ${i + 1}`}
            ></div>
          ))}
        </div>
      </div>

      {at_final_station && (
        <div className="mb-4 p-3 bg-slate-100 border border-slate-300 rounded-xl flex items-center gap-3">
          <Flag className="w-5 h-5 text-slate-500 flex-shrink-0" />
          <div>
            <div className="text-xs font-bold text-slate-700">Simulation Complete</div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Final Station: <strong>{current}</strong>. Reset simulation to replay scenario.
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={onNext}
          disabled={controlsDisabled}
          className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-bold text-sm transition-all duration-150 ${
            controlsDisabled
              ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
              : 'bg-blue-700 hover:bg-blue-800 active:bg-blue-900 text-white shadow-sm hover:shadow-md'
          }`}
        >
          <ChevronRight className="w-4 h-4" />
          {at_final_station ? 'Simulation Complete' : 'Next Station'}
        </button>

        <button
          onClick={onReset}
          disabled={disabled}
          className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold text-sm text-slate-600 border border-slate-200 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-60 disabled:cursor-not-allowed transition-all duration-150"
        >
          <RotateCcw className="w-4 h-4" />
          Reset
        </button>
      </div>
    </div>
  );
}
