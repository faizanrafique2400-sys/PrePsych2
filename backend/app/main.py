import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import settings
from app.models import (
    CopilotInsight,
    InsightStatus,
    PresageMetrics,
    PresageMetricsBatch,
    TranscriptionSegment,
)
from app.services import ollama as ollama_svc
from app.services import presage as presage_svc
from app.services import transcription as transcription_svc

app = FastAPI(title="PrePsych Therapy Copilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.preset_video_dir).mkdir(parents=True, exist_ok=True)

# In-memory copilot insights per session (id -> list of insights)
_copilot_insights: dict[str, list[CopilotInsight]] = {}


def _get_insights(session_id: str) -> list[CopilotInsight]:
    if session_id not in _copilot_insights:
        _copilot_insights[session_id] = []
    return _copilot_insights[session_id]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/preset-videos")
def list_preset_videos():
    """List preset video filenames for dropdown."""
    path = Path(settings.preset_video_dir)
    if not path.exists():
        return []
    names = [f.name for f in path.iterdir() if f.suffix.lower() in (".mp4", ".webm", ".mov")]
    return names


@app.get("/preset-videos/{filename}")
def get_preset_video(filename: str):
    """Stream preset video file."""
    path = Path(settings.preset_video_dir) / filename
    if not path.exists() or path.suffix.lower() not in (".mp4", ".webm", ".mov"):
        raise HTTPException(404, "Preset video not found")
    return FileResponse(path, media_type="video/mp4")


@app.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
):
    """Upload a video; returns path and session_id for later transcription/insights."""
    sid = session_id or str(uuid.uuid4())
    ext = Path(file.filename or "video.mp4").suffix or ".mp4"
    stored_name = f"{sid}{ext}"
    dest = Path(settings.upload_dir) / stored_name
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"session_id": sid, "path": str(dest), "filename": file.filename, "stored_filename": stored_name}


@app.post("/transcribe")
def transcribe(
    session_id: str,
    video_path: Optional[str] = None,
    use_preset: Optional[str] = None,
):
    """
    Transcribe video. Either video_path (stored filename in upload_dir) or use_preset (filename in preset_videos).
    """
    if use_preset:
        path = Path(settings.preset_video_dir) / use_preset
    elif video_path:
        path = Path(settings.upload_dir) / (Path(video_path).name or video_path)
    else:
        raise HTTPException(400, "Provide video_path or use_preset")
    if not path.exists():
        raise HTTPException(404, "Video file not found")
    try:
        full_text, segments = transcription_svc.transcribe_video(path)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {
        "session_id": session_id,
        "full_text": full_text,
        "segments": [TranscriptionSegment(**s) for s in segments],
    }


@app.post("/presage-metrics")
def post_presage_metrics(body: PresageMetricsBatch):
    """Receive Presage metrics from iOS app or C++ pipeline. Use this when you wire the app to feed data."""
    sid = body.session_id or "default"
    presage_svc.append_metrics(sid, body.metrics)
    return {"session_id": sid, "count": len(body.metrics)}


@app.get("/presage-metrics/{session_id}")
def get_presage_metrics(session_id: str):
    """Get stored Presage metrics for a session."""
    metrics = presage_svc.get_metrics_for_session(session_id)
    return {"session_id": session_id, "metrics": metrics}


@app.post("/generate-insight")
def generate_insight(
    session_id: str,
    transcript_segment: str,
    context: Optional[str] = None,
    use_mock_presage: bool = True,
):
    """
    Generate one copilot insight from transcript + Presage vitals using Ollama (local).
    If no Presage data for session and use_mock_presage=True, uses mock vitals for demo.
    """
    metrics = presage_svc.get_metrics_for_session(session_id)
    if not metrics and use_mock_presage:
        metrics = presage_svc.mock_metrics_for_demo(duration_sec=120.0)
    try:
        insight = ollama_svc.generate_mental_health_insight(
            transcript_segment=transcript_segment,
            presage_metrics=metrics,
            context=context,
        )
    except Exception as e:
        raise HTTPException(502, f"Ollama error (is Ollama running?): {e}")
    insights = _get_insights(session_id)
    insights.append(insight)
    return insight


@app.get("/insights/{session_id}")
def list_insights(session_id: str):
    return {"session_id": session_id, "insights": _get_insights(session_id)}


@app.patch("/insights/{session_id}/{insight_id}")
def acknowledge_insight(session_id: str, insight_id: str):
    """Mark an insight as acknowledged (addressed)."""
    insights = _get_insights(session_id)
    for idx, i in enumerate(insights):
        if i.id == insight_id:
            insights[idx] = CopilotInsight(
                id=i.id, text=i.text, status=InsightStatus.acknowledged,
                trigger_context=i.trigger_context, created_at=i.created_at,
            )
            return insights[idx]
    raise HTTPException(404, "Insight not found")


@app.post("/analyze-session")
def analyze_session(
    session_id: str,
    use_preset: Optional[str] = None,
    video_path: Optional[str] = None,
):
    """
    Full pipeline: transcribe video, then generate insights in chunks.
    Use either use_preset (filename) or video_path (uploaded file name).
    """
    try:
        path = None
        if use_preset:
            path = Path(settings.preset_video_dir) / use_preset
        elif video_path:
            path = Path(settings.upload_dir) / (Path(video_path).name or video_path)
        if not path or not path.exists():
            raise HTTPException(404, f"Video not found: {path}")

        full_text, segments = transcription_svc.transcribe_video(path)

        metrics = presage_svc.get_metrics_for_session(session_id)
        vitals_from_presage = bool(metrics)
        if not metrics:
            metrics = presage_svc.mock_metrics_for_demo(duration_sec=120.0)
        insights = _get_insights(session_id)
        chunk_size = max(1, len(segments) // 5)
        for i in range(0, len(segments), chunk_size):
            chunk = segments[i : i + chunk_size]
            text = " ".join(s["text"] for s in chunk).strip()
            if not text:
                continue
            try:
                insight = ollama_svc.generate_mental_health_insight(
                    transcript_segment=text,
                    presage_metrics=metrics,
                    context=f"Segment {i // chunk_size + 1}",
                )
                insights.append(insight)
            except Exception:
                pass

        pulse_vals = [m.pulse_bpm for m in metrics if m.pulse_bpm is not None]
        breath_vals = [m.breathing_bpm for m in metrics if m.breathing_bpm is not None]
        vitals_summary = {
            "heart_rate_bpm": round(sum(pulse_vals) / len(pulse_vals), 1) if pulse_vals else None,
            "breathing_bpm": round(sum(breath_vals) / len(breath_vals), 1) if breath_vals else None,
            "source": "presage" if vitals_from_presage else "mock",
        }

        return {
            "session_id": session_id,
            "full_text": full_text,
            "segments": [TranscriptionSegment(**s) for s in segments],
            "insights": insights,
            "vitals": vitals_summary,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
