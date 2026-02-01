"""
Presage metrics: accept POST from iOS app or C++ pipeline; provide mock for demo when no data.
The iOS app (SmartSpectra) sends data to Presage cloud; we don't have a direct web API for video.
So we store metrics that are POSTed here (e.g. from a companion script or when you wire the app)
and use mock metrics for uploaded/recorded video when none are available.
"""
from typing import Optional
from app.models import PresageMetrics


# In-memory store per session; in production use Redis or DB
_sessions: dict[str, list[PresageMetrics]] = {}


def get_metrics_for_session(session_id: Optional[str] = None) -> list[PresageMetrics]:
    if not session_id:
        return []
    return _sessions.get(session_id, [])


def append_metrics(session_id: str, metrics: list[PresageMetrics]) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = []
    _sessions[session_id].extend(metrics)


def mock_metrics_for_demo(duration_sec: float = 60.0) -> list[PresageMetrics]:
    """Generate plausible mock vitals for demo when Presage data isn't fed."""
    import random
    out = []
    t = 0.0
    step = 2.0  # every 2 seconds
    base_hr = 72
    base_br = 14
    while t < duration_sec:
        out.append(
            PresageMetrics(
                pulse_bpm=base_hr + random.uniform(-3, 5),
                breathing_bpm=base_br + random.uniform(-1, 2),
                timestamp_ms=int(t * 1000),
            )
        )
        t += step
    return out
