import { AlertTriangle, RotateCcw } from 'lucide-react';

export default function ErrorBanner({ message, onRetry, disabled }) {
  if (!message) return null;

  return (
    <div className="max-w-[1600px] mx-auto px-4 sm:px-6 pt-5">
      <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3 justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="text-sm font-bold text-red-700">SmartMetro backend unavailable</div>
            <div className="text-xs text-red-600 mt-0.5">{message}</div>
          </div>
        </div>
        <button
          onClick={onRetry}
          disabled={disabled}
          className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-white border border-red-200 text-red-700 text-xs font-bold hover:bg-red-100 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Retry
        </button>
      </div>
    </div>
  );
}
