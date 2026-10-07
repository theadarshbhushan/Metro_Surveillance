const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

async function request(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Accept: 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(data?.error || data?.message || `Request failed with status ${response.status}`);
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Unable to reach the SmartMetro backend. Please confirm Flask is running on port 5000.');
    }
    throw error;
  }
}

export function getSimulationState() {
  return request('/api/simulation/state');
}

export function advanceSimulation() {
  return request('/api/simulation/next', { method: 'POST' });
}

export function resetSimulation() {
  return request('/api/simulation/reset', { method: 'POST' });
}

// ---------------------------------------------------------------------------
// Real computer-vision data (Raspberry Pi edge node -> Flask)
// ---------------------------------------------------------------------------
export function getHealth() {
  return request('/api/health');
}

export function getVisionState() {
  return request('/api/vision/state');
}

export function getEvaluation() {
  return request('/api/vision/evaluation');
}

export function submitGroundTruth(payload) {
  return request('/api/vision/ground-truth', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export function clearEvaluation() {
  return request('/api/vision/evaluation', { method: 'DELETE' });
}

// Latest annotated snapshot (JPEG) for a coach; `tick` busts the browser cache.
export function visionFrameUrl(coachId, tick) {
  return `${API_BASE_URL}/api/vision/frame?coach_id=${encodeURIComponent(coachId)}&t=${tick}`;
}
