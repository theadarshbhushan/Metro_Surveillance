import { useState } from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { clearEvaluation, submitGroundTruth } from '../services/api';
import { getDensityConfig } from '../utils/densityUtils';

const NEXT_STATE = { undefined: 'OCCUPIED', OCCUPIED: 'EMPTY', EMPTY: undefined };
const SEAT_BTN = {
  OCCUPIED: 'bg-red-100 border-red-300 text-red-700',
  EMPTY: 'bg-emerald-100 border-emerald-300 text-emerald-700',
  undefined: 'bg-white border-slate-200 text-slate-400',
};

function Metric({ label, value, suffix = '', digits = 1 }) {
  const available = value !== null && value !== undefined;
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
      <div className="text-[9px] font-bold tracking-widest uppercase text-slate-400">{label}</div>
      <div className={`text-sm font-black ${available ? 'text-slate-800' : 'text-slate-300'}`}>
        {available ? `${Number(value).toFixed(digits)}${suffix}` : 'N/A'}
      </div>
    </div>
  );
}

function Row({ label, value, children }) {
  return (
    <div className="flex justify-between text-xs py-1 border-b border-slate-100 last:border-0">
      <span className="text-slate-500 font-medium">{label}</span>
      <span className="font-bold text-slate-800">{children ?? value}</span>
    </div>
  );
}

/**
 * Evaluator-entered ground truth vs what the system detected. Nothing here is derived from
 * the detector: with no samples every metric shows "Ground truth not available".
 */
export default function GroundTruthPanel({ coachId, seats, evaluation, onChanged }) {
  const [actual, setActual] = useState('');
  const [actualSeated, setActualSeated] = useState('');
  const [actualStanding, setActualStanding] = useState('');
  const [seatLabels, setSeatLabels] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const metrics = evaluation?.metrics;
  const latest = evaluation?.latest;
  const seatIds = Object.keys(seats || {});

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const payload = { coach_id: coachId, actual_people: Number(actual) };
    if (actualSeated !== '' && actualStanding !== '') {
      payload.actual_seated = Number(actualSeated);
      payload.actual_standing = Number(actualStanding);
    }
    if (Object.keys(seatLabels).length > 0) {
      payload.actual_seats = Object.fromEntries(Object.entries(seatLabels).filter(([, v]) => v));
    }
    setBusy(true);
    try {
      await submitGroundTruth(payload);
      setActual('');
      onChanged?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleClear = async () => {
    try {
      await clearEvaluation();
      onChanged?.();
    } catch (err) {
      setError(err.message);
    }
  };

  const accuracy = latest && latest.percentage_error != null ? Math.max(0, 100 - latest.percentage_error) : null;

  return (
    <div className="card p-5">
      <div className="section-label mb-0.5">Ground Truth & Accuracy</div>
      <div className="section-title mb-4">Actual vs System-Detected Density</div>

      <form onSubmit={handleSubmit} className="space-y-3 mb-4">
        <div className="grid grid-cols-3 gap-2">
          <label className="text-[10px] font-bold text-slate-500 col-span-3 sm:col-span-1">
            Actual people (counted by you)
            <input
              type="number" min="0" required value={actual} onChange={(e) => setActual(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-lg px-2 py-1.5 text-sm font-semibold"
            />
          </label>
          <label className="text-[10px] font-bold text-slate-500">
            Actual seated (optional)
            <input
              type="number" min="0" value={actualSeated} onChange={(e) => setActualSeated(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-lg px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-[10px] font-bold text-slate-500">
            Actual standing (optional)
            <input
              type="number" min="0" value={actualStanding} onChange={(e) => setActualStanding(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-lg px-2 py-1.5 text-sm"
            />
          </label>
        </div>

        {seatIds.length > 0 && (
          <div>
            <div className="text-[10px] font-bold text-slate-500 mb-1">
              Label real seat states (optional - click to cycle occupied / empty / unlabelled)
            </div>
            <div className="flex flex-wrap gap-1.5">
              {seatIds.map((id) => (
                <button
                  type="button" key={id}
                  onClick={() => setSeatLabels((prev) => ({ ...prev, [id]: NEXT_STATE[prev[id]] }))}
                  className={`px-2 py-1 rounded-md border text-[10px] font-bold ${SEAT_BTN[seatLabels[id]]}`}
                >
                  {id}{seatLabels[id] ? `: ${seatLabels[id]}` : ''}
                </button>
              ))}
            </div>
          </div>
        )}

        {error && <div className="text-xs text-red-600 font-semibold">{error}</div>}
        <div className="flex gap-2">
          <button type="submit" disabled={busy || actual === ''} className="btn-primary text-xs disabled:opacity-50">
            Record ground truth
          </button>
          <button type="button" onClick={handleClear} className="btn-secondary text-xs">Clear samples</button>
        </div>
      </form>

      {!metrics?.available ? (
        <div className="text-sm font-semibold text-slate-400 bg-slate-50 border border-dashed border-slate-300 rounded-lg px-4 py-3">
          Ground truth not available
        </div>
      ) : (
        <>
          {latest && (
            <div className="mb-4">
              <Row label="Actual People" value={latest.actual_people} />
              <Row label="Detected People" value={latest.detected_people} />
              <Row label="Difference" value={latest.absolute_error} />
              <Row label="Actual Density">
                <span className={getDensityConfig(latest.actual_density).textColor}>{latest.actual_density}</span>
              </Row>
              <Row label="Detected Density">
                <span className={getDensityConfig(latest.predicted_density).textColor}>{latest.predicted_density}</span>
              </Row>
              <Row label="Density Match">
                {latest.density_match
                  ? <CheckCircle2 className="w-4 h-4 text-emerald-600 inline" />
                  : <XCircle className="w-4 h-4 text-red-600 inline" />}
              </Row>
              <Row label="Detection Accuracy (this sample)" value={accuracy != null ? `${accuracy.toFixed(1)}%` : 'N/A'} />
            </div>
          )}
          <div className="text-[10px] font-bold tracking-widest uppercase text-slate-400 mb-2">
            Aggregate over {metrics.samples} sample{metrics.samples === 1 ? '' : 's'}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <Metric label="Count MAE" value={metrics.person_count_mae} digits={2} />
            <Metric label="Mean % error" value={metrics.person_count_mean_percentage_error} suffix="%" />
            <Metric label="Count accuracy" value={metrics.person_count_accuracy_percent} suffix="%" />
            <Metric label="Density accuracy" value={metrics.density_accuracy_percent} suffix="%" />
            <Metric label="Seat accuracy" value={metrics.seat_accuracy_percent} suffix="%" />
            <Metric label="Seated/standing acc." value={metrics.seated_standing_accuracy_percent} suffix="%" />
          </div>
        </>
      )}
    </div>
  );
}
