import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

export default function LoadMovement({ coaches, station }) {
  const totalInflow = coaches.reduce((s, c) => s + Math.max(0, c.movement), 0);
  const totalOutflow = coaches.reduce((s, c) => s + Math.abs(Math.min(0, c.movement)), 0);
  const netChange = Math.round((totalInflow - totalOutflow) * 10) / 10;

  return (
    <div className="card p-5">
      <div className="section-label mb-0.5">Station Load Movement</div>
      <div className="section-title mb-1">Change in Simulated Coach Load Since Previous Station</div>
      <div className="text-[10px] text-slate-400 mb-4 font-medium">
        {station.previous ? `${station.previous} → ${station.current}` : `Initial station — no movement recorded`}
      </div>

      <div className="space-y-2 mb-4">
        {coaches.map(coach => {
          const mv = coach.movement;
          const isPos = mv > 0;
          const isNeg = mv < 0;
          const isZero = mv === 0;

          return (
            <div key={coach.id} className="flex items-center gap-3">
              <div className="w-16 text-xs font-bold text-slate-600 flex-shrink-0">
                Coach {coach.id}
              </div>

              {/* Bar */}
              <div className="flex-1 h-5 bg-slate-100 rounded-full relative overflow-hidden">
                {isPos && (
                  <div
                    className="absolute left-0 h-full bg-emerald-400 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min((Math.abs(mv) / 40) * 100, 100)}%` }}
                  ></div>
                )}
                {isNeg && (
                  <div
                    className="absolute right-0 h-full bg-red-400 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min((Math.abs(mv) / 40) * 100, 100)}%` }}
                  ></div>
                )}
              </div>

              {/* Value */}
              <div className={`flex items-center gap-1 w-24 flex-shrink-0 ${
                isPos ? 'text-emerald-600' : isNeg ? 'text-red-500' : 'text-slate-400'
              }`}>
                {isPos && <ArrowUp className="w-3.5 h-3.5" />}
                {isNeg && <ArrowDown className="w-3.5 h-3.5" />}
                {isZero && <Minus className="w-3.5 h-3.5" />}
                <span className="text-sm font-bold">
                  {isPos ? '+' : ''}{mv}
                </span>
                <span className="text-[9px] text-slate-400">units</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary totals */}
      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-100">
        <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-2.5 text-center">
          <div className="text-xs font-black text-emerald-600">+{totalInflow}</div>
          <div className="text-[9px] font-bold tracking-widest uppercase text-emerald-500 mt-0.5">Total Inflow</div>
        </div>
        <div className="bg-red-50 border border-red-100 rounded-lg p-2.5 text-center">
          <div className="text-xs font-black text-red-600">-{totalOutflow}</div>
          <div className="text-[9px] font-bold tracking-widest uppercase text-red-500 mt-0.5">Total Outflow</div>
        </div>
        <div className={`border rounded-lg p-2.5 text-center ${netChange >= 0 ? 'bg-slate-50 border-slate-100' : 'bg-slate-50 border-slate-100'}`}>
          <div className={`text-xs font-black ${netChange > 0 ? 'text-emerald-600' : netChange < 0 ? 'text-red-600' : 'text-slate-500'}`}>
            {netChange > 0 ? '+' : ''}{netChange}
          </div>
          <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400 mt-0.5">Net Change</div>
        </div>
      </div>

      <div className="mt-2 text-[9px] text-slate-400 text-center font-medium">
        Values represent simulated load units — not literal passenger counts
      </div>
    </div>
  );
}
