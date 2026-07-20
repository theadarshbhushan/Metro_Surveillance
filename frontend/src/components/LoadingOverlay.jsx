import { Loader2 } from 'lucide-react';

export default function LoadingOverlay({ label = 'Syncing simulation state' }) {
  return (
    <div className="fixed inset-0 z-[70] bg-slate-950/15 backdrop-blur-[1px] flex items-center justify-center">
      <div className="bg-white border border-slate-200 rounded-xl shadow-xl px-5 py-4 flex items-center gap-3">
        <Loader2 className="w-5 h-5 text-blue-700 animate-spin" />
        <span className="text-sm font-bold text-slate-700">{label}</span>
      </div>
    </div>
  );
}
