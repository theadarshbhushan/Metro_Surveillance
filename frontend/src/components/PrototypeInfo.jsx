import { Info } from 'lucide-react';

export default function PrototypeInfo() {
  const items = [
    { label: 'Phase', value: '1 — Software Simulation' },
    { label: 'Data Source', value: 'Simulated Station Dataset (CSV)' },
    { label: 'Decision Engine', value: 'Rule-Based Crowd Distribution' },
    { label: 'Backend', value: 'Python Flask REST API' },
    { label: 'Future Integration', value: 'Edge Sensors + Computer Vision (YOLO)' },
  ];

  return (
    <div className="flex items-start gap-3 p-4 bg-slate-50 border border-slate-200 rounded-xl">
      <Info className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
      <div>
        <div className="text-[10px] font-bold tracking-widest uppercase text-slate-400 mb-2">Prototype Status</div>
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          {items.map((item, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="text-[10px] font-semibold text-slate-400">{item.label}:</span>
              <span className="text-[10px] font-bold text-slate-600">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
