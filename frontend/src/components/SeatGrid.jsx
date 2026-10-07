const SEAT_STYLES = {
  OCCUPIED: 'bg-red-50 border-red-300 text-red-700',
  EMPTY: 'bg-emerald-50 border-emerald-300 text-emerald-700',
  UNCERTAIN: 'bg-amber-50 border-amber-300 text-amber-700',
};

const SEAT_LABELS = { OCCUPIED: 'OCCUPIED', EMPTY: 'EMPTY', UNCERTAIN: 'UNCERTAIN' };

/** Real seat states from the vision pipeline. Track IDs are temporary per-session numbers. */
export default function SeatGrid({ seats, summary }) {
  const ids = Object.keys(seats || {});

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold tracking-widest uppercase text-slate-400">Seat States</span>
        <span className="text-[10px] font-semibold text-slate-500">
          Occupied: <strong className="text-red-600">{summary.occupied_seats}</strong>
          {' · '}Empty: <strong className="text-emerald-600">{summary.empty_seats}</strong>
          {' · '}Uncertain: <strong className="text-amber-600">{summary.uncertain_seats}</strong>
        </span>
      </div>

      {ids.length === 0 ? (
        <div className="text-xs text-slate-400 italic">
          No seat polygons configured for this coach (run tools/seat_mapper.py).
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {ids.map((id) => {
            const seat = seats[id];
            return (
              <div
                key={id}
                className={`rounded-lg border px-2.5 py-2 transition-colors duration-300 ${SEAT_STYLES[seat.status] || SEAT_STYLES.UNCERTAIN}`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-black">{id}</span>
                  {seat.track_id != null && (
                    <span className="text-[9px] font-semibold opacity-70">P{seat.track_id}</span>
                  )}
                </div>
                <div className="text-[9px] font-bold tracking-widest">{SEAT_LABELS[seat.status] || seat.status}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
