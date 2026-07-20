/**
 * Centralized density helpers for colors, labels, movement display, and
 * aggregate occupancy values derived from backend coach data.
 */

export const DENSITY_CONFIG = {
  LOW: {
    label: 'LOW DENSITY',
    badge: 'LOW',
    barColor: 'bg-emerald-500',
    borderColor: 'border-emerald-300',
    bgColor: 'bg-emerald-50',
    textColor: 'text-emerald-700',
    dotColor: 'bg-emerald-500',
    hex: '#10b981',
    lightHex: '#d1fae5',
  },
  MODERATE: {
    label: 'MODERATE DENSITY',
    badge: 'MODERATE',
    barColor: 'bg-amber-500',
    borderColor: 'border-amber-300',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-700',
    dotColor: 'bg-amber-500',
    hex: '#f59e0b',
    lightHex: '#fef3c7',
  },
  HIGH: {
    label: 'HIGH DENSITY',
    badge: 'HIGH',
    barColor: 'bg-orange-500',
    borderColor: 'border-orange-300',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-700',
    dotColor: 'bg-orange-500',
    hex: '#f97316',
    lightHex: '#ffedd5',
  },
  CRITICAL: {
    label: 'CRITICAL DENSITY',
    badge: 'CRITICAL',
    barColor: 'bg-red-500',
    borderColor: 'border-red-300',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    dotColor: 'bg-red-500',
    hex: '#ef4444',
    lightHex: '#fee2e2',
  },
};

export function getDensityConfig(status) {
  return DENSITY_CONFIG[status] || DENSITY_CONFIG.LOW;
}

export function getOccupancyBarColor(pct) {
  if (pct <= 40) return '#10b981';
  if (pct <= 65) return '#f59e0b';
  if (pct <= 85) return '#f97316';
  return '#ef4444';
}

export function formatMovement(movement) {
  if (movement === 0) return { text: '- No change', color: 'text-slate-400', symbol: '-' };
  if (movement > 0) return { text: `+${movement} units`, color: 'text-emerald-600', symbol: '↑' };
  return { text: `${movement} units`, color: 'text-blue-600', symbol: '↓' };
}

export function getOverallDensity(coaches) {
  if (!coaches || coaches.length === 0) return 'LOW';
  const avg = coaches.reduce((s, c) => s + c.occupancy_percentage, 0) / coaches.length;
  if (avg <= 40) return 'LOW';
  if (avg <= 65) return 'MODERATE';
  if (avg <= 85) return 'HIGH';
  return 'CRITICAL';
}

export function getAverageOccupancy(coaches) {
  if (!coaches || coaches.length === 0) return 0;
  const avg = coaches.reduce((s, c) => s + c.occupancy_percentage, 0) / coaches.length;
  return Math.round(avg * 10) / 10;
}
