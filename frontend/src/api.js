const API = '/api';

export async function health() {
  const r = await fetch(`${API}/health`);
  return r.json();
}

export async function listPresetVideos() {
  const r = await fetch(`${API}/preset-videos`);
  return r.json();
}

export async function getPresetVideoUrl(filename) {
  return `${API}/preset-videos/${encodeURIComponent(filename)}`;
}

export async function uploadVideo(file, sessionId) {
  const form = new FormData();
  form.append('file', file);
  if (sessionId) form.append('session_id', sessionId);
  const r = await fetch(`${API}/upload-video`, { method: 'POST', body: form });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function transcribe(sessionId, opts = {}) {
  const params = new URLSearchParams({ session_id: sessionId });
  if (opts.use_preset) params.set('use_preset', opts.use_preset);
  if (opts.video_path) params.set('video_path', opts.video_path);
  const r = await fetch(`${API}/transcribe?${params}`, { method: 'POST' });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function postPresageMetrics(sessionId, metrics) {
  const r = await fetch(`${API}/presage-metrics`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, metrics }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getPresageMetrics(sessionId) {
  const r = await fetch(`${API}/presage-metrics/${encodeURIComponent(sessionId)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function generateInsight(sessionId, transcriptSegment, context, useMockPresage = true) {
  const params = new URLSearchParams({
    session_id: sessionId,
    transcript_segment: transcriptSegment,
    use_mock_presage: useMockPresage,
  });
  if (context) params.set('context', context);
  const r = await fetch(`${API}/generate-insight?${params}`, { method: 'POST' });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listInsights(sessionId) {
  const r = await fetch(`${API}/insights/${encodeURIComponent(sessionId)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function acknowledgeInsight(sessionId, insightId) {
  const r = await fetch(`${API}/insights/${encodeURIComponent(sessionId)}/${encodeURIComponent(insightId)}`, {
    method: 'PATCH',
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function analyzeSession(sessionId, opts = {}) {
  const params = new URLSearchParams({ session_id: sessionId });
  if (opts.use_preset) params.set('use_preset', opts.use_preset);
  if (opts.video_path) params.set('video_path', opts.video_path);
  const r = await fetch(`${API}/analyze-session?${params}`, { method: 'POST' });
  const text = await r.text();
  if (!r.ok) {
    let msg = text;
    try {
      const body = JSON.parse(text);
      if (body.detail) msg = typeof body.detail === 'string' ? body.detail : body.detail[0]?.msg || text;
    } catch (_) {}
    throw new Error(msg);
  }
  return JSON.parse(text);
}
