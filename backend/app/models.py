from pydantic import BaseModel
from typing import Optional
from enum import Enum


class InsightStatus(str, Enum):
    pending = "pending"
    acknowledged = "acknowledged"


class PresageMetrics(BaseModel):
    """Vitals from Presage SmartSpectra (heart rate, breathing, etc.)."""
    pulse_bpm: Optional[float] = None
    breathing_bpm: Optional[float] = None
    hrv_ms: Optional[float] = None
    prq: Optional[float] = None  # pulse respiration quotient
    timestamp_ms: Optional[int] = None


class PresageMetricsBatch(BaseModel):
    """Batch of Presage metrics (e.g. from iOS app or C++ pipeline)."""
    session_id: Optional[str] = None
    metrics: list[PresageMetrics] = []


class TranscriptionSegment(BaseModel):
    start: float
    end: float
    text: str


class CopilotInsight(BaseModel):
    id: str
    text: str
    status: InsightStatus = InsightStatus.pending
    trigger_context: Optional[str] = None  # e.g. "Mention of father + elevated HR"
    created_at: Optional[str] = None
