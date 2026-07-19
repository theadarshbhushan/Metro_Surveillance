import { AlertCircle, TrendingUp, CheckCircle, Navigation, Info } from 'lucide-react';

export default function CrowdMonitor({ coaches, recommendation, station }) {
  const criticalCoaches = coaches.filter(c => c.density_status === 'CRITICAL');
  const highCoaches = coaches.filter(c => c.density_status === 'HIGH');
  const bestCoach = coaches.find(c => c.id === recommendation.coach_id);

  const alerts = [
    ...criticalCoaches.map(c => ({
      level: 'CRITICAL',
      icon: AlertCircle,
      iconColor: 'text-red-600',
      bg: 'bg-red-50',
      border: 'border-red-200',
      textColor: 'text-red-700',
      badgeBg: 'bg-red-600',
      message: `Coach ${c.id} approaching maximum simulated capacity (${c.occupancy_percentage}%)`,
      sub: station.current,
    })),
    ...highCoaches.map(c => ({
      level: 'HIGH DENSITY',
      icon: TrendingUp,
      iconColor: 'text-orange-600',
      bg: 'bg-orange-50',
      border: 'border-orange-200',
      textColor: 'text-orange-700',
      badgeBg: 'bg-orange-500',
      message: `Coach ${c.id} at ${c.occupancy_percentage}% — elevated load detected`,
      sub: station.current,
    })),
    coaches.some(c => c.id === 4 && (c.density_status === 'CRITICAL' || c.density_status === 'HIGH'))
      ? {
          level: 'HIGH INFLOW',
          icon: TrendingUp,
          iconColor: 'text-amber-600',
          bg: 'bg-amber-50',
          border: 'border-amber-200',
          textColor: 'text-amber-700',
          badgeBg: 'bg-amber-500',
          message: 'Passenger accumulation detected near elevator/escalator access point (Coach 4)',
          sub: station.current,
        }
      : null,
    bestCoach
      ? {
          level: 'OPTIMAL',
          icon: CheckCircle,
          iconColor: 'text-emerald-600',
          bg: 'bg-emerald-50',
          border: 'border-emerald-200',
          textColor: 'text-emerald-700',
          badgeBg: 'bg-emerald-500',
          message: `Coach ${bestCoach.id} has ${bestCoach.available_capacity} units capacity available (${100 - bestCoach.occupancy_percentage}% free)`,
          sub: station.current,
        }
      : null,
    {
      level: 'RECOMMENDATION',
      icon: Navigation,
      iconColor: 'text-blue-600',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      textColor: 'text-blue-700',
      badgeBg: 'bg-blue-600',
      message: `Redirect boarding flow toward Coach ${recommendation.coach_id} for balanced distribution`,
      sub: station.current,
    },
  ].filter(Boolean);

  return (
    <div className="card p-5">
      <div className="section-label mb-0.5">Crowd Monitor</div>
      <div className="section-title mb-4">Operational Alerts & System Notices</div>

      <div className="space-y-2">
        {alerts.map((alert, i) => {
          const Icon = alert.icon;
          return (
            <div
              key={i}
              className={`flex items-start gap-3 p-3 rounded-lg border ${alert.bg} ${alert.border} transition-all duration-300`}
              style={{ animationDelay: `${i * 50}ms` }}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${alert.iconColor}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className={`text-[8px] font-black tracking-widest text-white px-1.5 py-0.5 rounded-full ${alert.badgeBg}`}>
                    {alert.level}
                  </span>
                </div>
                <div className={`text-xs font-medium ${alert.textColor}`}>{alert.message}</div>
                <div className="text-[9px] text-slate-400 mt-0.5 font-medium">{alert.sub}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
