import { ArrowDown, Users, MoveDown } from 'lucide-react';

export default function PlatformAccess() {
  return (
    <div className="flex flex-col items-center justify-start pl-4 flex-shrink-0 w-32">
      {/* Connector line from Coach 4 */}
      <div className="w-px h-4 bg-orange-200"></div>

      {/* Elevator card */}
      <div className="bg-orange-50 border-2 border-orange-200 rounded-xl p-3 flex flex-col items-center gap-1.5 w-full">
        {/* Elevator icon */}
        <div className="w-9 h-9 bg-orange-100 border border-orange-300 rounded-lg flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="4" y="2" width="16" height="20" rx="2"/>
            <path d="M9 9l3-3 3 3"/>
            <path d="M9 15l3 3 3-3"/>
            <line x1="12" y1="6" x2="12" y2="18"/>
          </svg>
        </div>

        <div className="text-center">
          <div className="text-[8px] font-black tracking-widest uppercase text-orange-700 leading-tight">
            ELEVATOR /
          </div>
          <div className="text-[8px] font-black tracking-widest uppercase text-orange-700 leading-tight">
            ESCALATOR
          </div>
          <div className="text-[8px] font-semibold text-orange-500 mt-0.5">Platform Access</div>
        </div>

        {/* HIGH INFLOW badge */}
        <div className="bg-red-100 border border-red-300 rounded-full px-2 py-0.5">
          <span className="text-[8px] font-black tracking-widest uppercase text-red-600">HIGH INFLOW</span>
        </div>
      </div>

      {/* Flow arrows */}
      <div className="flex flex-col items-center gap-0.5 my-1.5">
        <MoveDown className="w-4 h-4 text-orange-400" />
        <MoveDown className="w-4 h-4 text-orange-300" />
        <MoveDown className="w-4 h-4 text-orange-200" />
      </div>

      {/* Passenger icons */}
      <div className="flex gap-1 mb-1">
        {[0, 1, 2].map(i => (
          <div key={i} className="flex flex-col items-center gap-0.5 opacity-60">
            <div className="w-3 h-3 rounded-full bg-orange-400"></div>
            <div className="w-2 h-3 rounded-sm bg-orange-400"></div>
          </div>
        ))}
      </div>

      {/* Annotation */}
      <div className="mt-1 bg-white border border-slate-200 rounded-lg p-2 w-full">
        <p className="text-[8px] text-slate-500 text-center leading-relaxed font-medium">
          Passenger accumulation tendency near platform access
        </p>
      </div>
    </div>
  );
}
