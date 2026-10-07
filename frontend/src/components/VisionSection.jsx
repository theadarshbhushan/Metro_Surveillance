import { useEffect, useState } from 'react';
import { Radio, WifiOff } from 'lucide-react';
import SeatGrid from './SeatGrid';
import SurveillanceView from './SurveillanceView';
import GroundTruthPanel from './GroundTruthPanel';
import AlertsPanel from './AlertsPanel';
import { getDensityConfig } from '../utils/densityUtils';

function Stat({ label, value, tone = 'text-slate-800' }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
      <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400">{label}</div>
      <div className={`text-lg font-black leading-tight ${tone}`}>{value}</div>
    </div>
  );
}

/**
 * Real computer-vision monitor: everything here comes from Flask's /api/vision/* state,
 * which is fed by the edge node (camera -> YOLO -> seat mapping -> telemetry).
 */
export default function VisionSection({ vision, evaluation, offline, onRefresh }) {
  const coaches = vision?.coaches || {};
  const coachIds = Object.keys(coaches);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    if (coachIds.length > 0 && !coachIds.includes(selected)) setSelected(coachIds[0]);
  }, [coachIds.join(','), selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const coach = selected ? coaches[selected] : null;
  const cfg = coach ? getDensityConfig(coach.density_status) : null;

  return (
    <section className="space-y-5" id="vision">
      <div className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <div className="section-label mb-0.5">Live Vision Monitor · Raspberry Pi Edge AI</div>
            <div className="section-title">Real Passenger Detection, Seat Occupancy & Density</div>
          </div>
          <div className="flex items-center gap-2">
            {coachIds.map((id) => (
              <button
                key={id}
                onClick={() => setSelected(id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold border ${
                  id === selected ? 'bg-blue-700 text-white border-blue-700' : 'bg-white text-slate-600 border-slate-200'
                }`}
              >
                {id}
              </button>
            ))}
            {coach && (
              <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold tracking-widest px-2.5 py-1 rounded-full border ${
                coach.live ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-slate-100 border-slate-300 text-slate-500'
              }`}>
                {coach.live ? <Radio className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
                {coach.live ? 'LIVE' : `STALE · ${coach.age_seconds}s`}
              </span>
            )}
          </div>
        </div>

        {offline && (
          <div className="mb-3 text-xs font-semibold text-red-600">
            Backend not reachable - showing last known vision data.
          </div>
        )}

        {!coach ? (
          <div className="text-sm text-slate-500 bg-slate-50 border border-dashed border-slate-300 rounded-xl px-4 py-6 text-center">
            <div className="font-bold text-slate-600 mb-1">No vision telemetry received yet</div>
            Start the edge pipeline, e.g. <code className="bg-white border rounded px-1">python run_demo.py</code> or{' '}
            <code className="bg-white border rounded px-1">python run_vision.py --source videos/coach.mp4</code>.
            Until then the dashboard uses simulated data.
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-5 gap-5">
            <div className="xl:col-span-3">
              <SurveillanceView coachId={coach.coach_id} live={coach.live} />
              {coach.fps && (
                <div className="mt-2 text-[10px] text-slate-400 font-medium">
                  Capture {coach.fps.capture ?? '-'} fps · Inference {coach.fps.inference ?? '-'} fps ·
                  Telemetry {coach.fps.telemetry ?? '-'} /s · Frame {coach.frame ?? '-'}
                </div>
              )}
            </div>

            <div className="xl:col-span-2 space-y-4">
              <div className={`rounded-xl border-2 p-4 ${cfg.bgColor} ${cfg.borderColor}`}>
                <div className="text-[10px] font-bold tracking-widest uppercase text-slate-500">Coach {coach.coach_id}</div>
                <div className="flex items-end justify-between">
                  <div>
                    <div className="text-3xl font-black text-slate-800">
                      {coach.total_people}<span className="text-base text-slate-400"> / {coach.max_passengers}</span>
                    </div>
                    <div className="text-xs font-semibold text-slate-500">
                      People · Occupancy {coach.occupancy_percentage}%
                    </div>
                  </div>
                  <span className={`text-xs font-black tracking-widest px-3 py-1 rounded-full border ${cfg.bgColor} ${cfg.borderColor} ${cfg.textColor}`}>
                    {coach.density_status}
                  </span>
                </div>
                <div className="w-full h-2 bg-white/70 rounded-full overflow-hidden mt-3">
                  <div className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, coach.occupancy_percentage)}%`, backgroundColor: cfg.hex }} />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <Stat label="Seated" value={coach.seated_people} tone="text-blue-700" />
                <Stat label="Standing" value={coach.standing_people} tone="text-fuchsia-700" />
                <Stat label="Unknown" value={coach.unknown_people} tone="text-slate-500" />
              </div>

              <SeatGrid seats={coach.seats} summary={coach} />
              {coach.seat_occupancy_percentage != null && (
                <div className="text-[10px] text-slate-400 font-medium">
                  Seat usage {coach.seat_occupancy_percentage}% (occupied seats / seats) - separate from crowd
                  density, which is people / {coach.max_passengers} capacity.
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <GroundTruthPanel
          coachId={coach?.coach_id || 'C1'}
          seats={coach?.seats}
          evaluation={evaluation}
          onChanged={onRefresh}
        />
        <AlertsPanel alerts={vision?.alerts} />
      </div>
    </section>
  );
}
