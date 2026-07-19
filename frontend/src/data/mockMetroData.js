/**
 * mockMetroData.js
 * Centralized simulation states matching the exact Flask API response structure.
 * All UI components receive data via props — no hardcoding in JSX.
 * Replace this file's data source with Flask API calls in Phase 2.
 */

// All 8 stations with their coach loads (from backend/data/stations.csv)
export const ALL_STATIONS = [
  { name: 'Andheri',    coaches: [30, 25, 35, 55] },
  { name: 'Vile Parle', coaches: [42, 38, 50, 68] },
  { name: 'Santacruz',  coaches: [55, 44, 62, 78] },
  { name: 'Bandra',     coaches: [48, 52, 70, 88] },
  { name: 'Mahim',      coaches: [62, 39, 58, 82] },
  { name: 'Dadar',      coaches: [75, 65, 72, 91] },
  { name: 'Parel',      coaches: [58, 70, 64, 79] },
  { name: 'Masjid',     coaches: [40, 35, 45, 60] },
];

const CAPACITY = 100;

/**
 * Given a station index, build the full API-shaped state object.
 */
export function buildStateForIndex(index) {
  const total = ALL_STATIONS.length;
  const clampedIndex = Math.max(0, Math.min(index, total - 1));

  const current = ALL_STATIONS[clampedIndex];
  const previous = clampedIndex > 0 ? ALL_STATIONS[clampedIndex - 1] : null;
  const next = clampedIndex < total - 1 ? ALL_STATIONS[clampedIndex + 1] : null;

  const coaches = current.coaches.map((load, i) => {
    const prevLoad = previous ? previous.coaches[i] : load;
    const occupancy = Math.round((load / CAPACITY) * 100 * 10) / 10;
    const available = Math.round((CAPACITY - load) * 10) / 10;
    const movement = Math.round((load - prevLoad) * 10) / 10;
    return {
      id: i + 1,
      current_load: load,
      capacity: CAPACITY,
      occupancy_percentage: occupancy,
      available_capacity: available,
      density_status: getDensityStatus(occupancy),
      movement,
    };
  });

  // Recommend least occupied coach
  const sortedCoaches = [...coaches].sort(
    (a, b) => a.occupancy_percentage - b.occupancy_percentage
  );
  const best = sortedCoaches[0];
  const recommendation = {
    coach_id: best.id,
    occupancy_percentage: best.occupancy_percentage,
    available_capacity: best.available_capacity,
    density_status: best.density_status,
    reason: `Coach ${best.id} currently has the highest available capacity (${best.available_capacity} units free, ${best.occupancy_percentage}% occupied) and provides the best option for balanced passenger distribution.`,
  };

  return {
    station: {
      current: current.name,
      previous: previous?.name ?? null,
      next: next?.name ?? null,
      index: clampedIndex,
      total,
      at_final_station: clampedIndex === total - 1,
    },
    coaches,
    recommendation,
  };
}

function getDensityStatus(pct) {
  if (pct <= 40) return 'LOW';
  if (pct <= 65) return 'MODERATE';
  if (pct <= 85) return 'HIGH';
  return 'CRITICAL';
}

// Default demo state: Dadar (index 5) — Coach 4 is CRITICAL at 91%
export const INITIAL_STATE = buildStateForIndex(5);
