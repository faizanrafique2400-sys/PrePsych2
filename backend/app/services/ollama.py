import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from app.config import settings
from app.models import CopilotInsight, InsightStatus, PresageMetrics


def _ollama_chat(messages: list[dict], model: str = "llama3.2") -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {"model": model, "messages": messages, "stream": False}
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "").strip()


def _summarize_vitals(metrics_list: list[PresageMetrics]) -> str:
    if not metrics_list:
        return "No vitals data available."
    recent = metrics_list[-10:]
    pulse_vals = [m.pulse_bpm for m in recent if m.pulse_bpm is not None]
    breath_vals = [m.breathing_bpm for m in recent if m.breathing_bpm is not None]
    parts = []
    if pulse_vals:
        avg_p = sum(pulse_vals) / len(pulse_vals)
        parts.append(f"heart rate ~{avg_p:.0f} BPM")
    if breath_vals:
        avg_b = sum(breath_vals) / len(breath_vals)
        parts.append(f"breathing ~{avg_b:.1f} BPM")
    return "; ".join(parts) if parts else "No vitals available."


def generate_mental_health_insight(
    transcript_segment: str,
    presage_metrics: list[PresageMetrics],
    context: Optional[str] = None,
    model: str = "llama3.2",
) -> CopilotInsight:
    """
    Use Ollama to generate a short therapist-copilot insight from transcript + vitals.
    Keeps everything local for privacy.
    """
    vitals_summary = _summarize_vitals(presage_metrics)
    system_prompt = """You are a clinical psychology assistant helping a therapist in real time.
You see a short transcript of what the client said and a summary of their vitals (heart rate, breathing from contactless measurement).
Output ONE short, actionable insight only: e.g. "Possible discomfort when discussing [topic]; consider gentle follow-up."
or "Vitals steady; client seems calm." or "Elevated heart rate when mentioning [X]; worth exploring."
Keep each response to 1-2 sentences. No preamble. No bullet points. Plain text only."""

    user_content = f"Transcript excerpt:\n{transcript_segment}\n\nVitals: {vitals_summary}"
    if context:
        user_content += f"\nContext: {context}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    content = _ollama_chat(messages, model=model)
    trigger = context or "Transcript + vitals"
    return CopilotInsight(
        id=str(uuid.uuid4()),
        text=content,
        status=InsightStatus.pending,
        trigger_context=trigger,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
