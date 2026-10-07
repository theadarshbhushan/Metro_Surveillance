import { useEffect, useState } from 'react';
import { Camera, CameraOff } from 'lucide-react';
import { visionFrameUrl } from '../services/api';

/**
 * Shows the latest ANNOTATED snapshot posted by the edge node (bounding boxes, track IDs,
 * seat polygons, SEATED/STANDING labels, density). Raw video is never streamed through Flask.
 */
export default function SurveillanceView({ coachId, live, refreshMs = 1000 }) {
  const [tick, setTick] = useState(() => Date.now());
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!live) return undefined;
    const id = setInterval(() => setTick(Date.now()), refreshMs);
    return () => clearInterval(id);
  }, [live, refreshMs]);

  return (
    <div className="relative bg-slate-900 rounded-xl overflow-hidden border border-slate-700 min-h-[220px] flex items-center justify-center">
      {!failed && (
        <img
          src={visionFrameUrl(coachId, tick)}
          alt={`Annotated camera view of coach ${coachId}`}
          className="w-full h-auto max-h-[460px] object-contain"
          onError={() => setFailed(true)}
          onLoad={() => setFailed(false)}
        />
      )}
      {failed && (
        <div className="text-center text-slate-400 p-6">
          <CameraOff className="w-8 h-8 mx-auto mb-2" />
          <div className="text-xs font-semibold">No annotated frame received yet</div>
          <div className="text-[10px] mt-1">The edge node uploads one annotated snapshot per second.</div>
        </div>
      )}
      <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-black/60 text-white text-[9px] font-bold tracking-widest px-2 py-1 rounded-full">
        <Camera className="w-3 h-3" />
        {live ? 'LIVE · ANNOTATED' : 'LAST FRAME · STALE'}
      </div>
    </div>
  );
}
