import { Train, RefreshCw, Activity } from 'lucide-react';

export default function Header({ onReset, disabled }) {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-[1600px] mx-auto px-6 h-14 flex items-center justify-between gap-4">

        {/* Brand */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center shadow-sm">
            <Train className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-bold text-slate-900 tracking-wide">SMARTMETRO</span>
              <span className="hidden sm:inline text-[10px] font-medium text-slate-400 tracking-widest uppercase">
                Crowd Intelligence & Decision Support
              </span>
            </div>
          </div>
        </div>

        {/* Centre label */}
        <div className="hidden md:flex items-center gap-2 text-slate-500">
          <span className="text-xs font-semibold tracking-widest uppercase text-blue-700">
            Mumbai Metro — Line Simulation
          </span>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* System status */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 border border-emerald-200 rounded-full">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-[10px] font-bold tracking-widest text-emerald-700 uppercase">System Active</span>
          </div>

          {/* Phase badge */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 border border-blue-200 rounded-full">
            <Activity className="w-3 h-3 text-blue-600" />
            <span className="text-[10px] font-bold tracking-widest text-blue-700 uppercase">Software Simulation</span>
          </div>

          {/* Review label */}
          <span className="hidden lg:block text-[10px] text-slate-400 font-medium">Review Prototype · Phase 1</span>

          {/* Reset button */}
          <button
            onClick={onReset}
            disabled={disabled}
            className="flex items-center gap-1.5 px-3 py-1.5 text-slate-600 hover:text-blue-700 hover:bg-blue-50 border border-slate-200 hover:border-blue-200 rounded-lg transition-all duration-150 text-xs font-semibold disabled:opacity-60 disabled:cursor-not-allowed"
            title="Reset Simulation"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Reset</span>
          </button>
        </div>
      </div>
    </header>
  );
}
