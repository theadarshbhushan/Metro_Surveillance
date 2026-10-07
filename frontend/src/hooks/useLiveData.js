import { useCallback, useEffect, useRef, useState } from 'react';
import { getEvaluation, getVisionState } from '../services/api';

/**
 * Polls the backend's vision endpoints so the dashboard follows the edge node in real time.
 * The frontend never talks to YOLO or the camera: it only reads Flask's latest telemetry.
 * Failures keep the last good data and surface a flag instead of throwing.
 */
export default function useLiveData(intervalMs = 1500) {
  const [vision, setVision] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [offline, setOffline] = useState(false);
  const busy = useRef(false);

  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const [v, e] = await Promise.all([getVisionState(), getEvaluation()]);
      setVision(v);
      setEvaluation(e);
      setOffline(false);
    } catch {
      setOffline(true);
    } finally {
      busy.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

  return { vision, evaluation, offline, refresh };
}
