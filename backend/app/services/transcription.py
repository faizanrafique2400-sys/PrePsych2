from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from app.config import settings

# Prefer faster_whisper for speed; fallback to openai-whisper
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

if not HAS_FASTER_WHISPER:
    try:
        import whisper
    except ImportError:
        whisper = None
else:
    whisper = None


def _ensure_audio_path(path: Path) -> str:
    """Convert .webm to .wav via ffmpeg if needed so Whisper can read it."""
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")
    suffix = path.suffix.lower()
    if suffix in (".mp4", ".m4a", ".mp3", ".wav", ".flac", ".ogg"):
        return str(path)
    if suffix == ".webm":
        out = path.with_suffix(".wav")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(path), "-vn", "-acodec", "pcm_s16le", "-ar", "16000", str(out)],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg not found. Install it to transcribe .webm (e.g. brew install ffmpeg on macOS)."
            )
        except subprocess.CalledProcessError as e:
            err = (e.stderr or e.stdout or b"").decode(errors="replace")
            raise RuntimeError(f"ffmpeg failed: {err[:500]}")
        if not out.exists():
            raise RuntimeError("ffmpeg did not produce output file")
        return str(out)
    return str(path)


def transcribe_video(video_path: str | Path) -> tuple[str, list[dict]]:
    """
    Transcribe audio from video file. Returns (full_text, segments).
    segments: list of {start, end, text}
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    audio_path = _ensure_audio_path(path)

    if HAS_FASTER_WHISPER and getattr(settings, "use_faster_whisper", True):
        return _transcribe_faster_whisper(audio_path)
    if whisper is not None:
        return _transcribe_openai_whisper(audio_path)
    raise RuntimeError("Install faster-whisper or openai-whisper: pip install faster-whisper (or openai-whisper)")


def _transcribe_faster_whisper(path: str) -> tuple[str, list[dict]]:
    # base.en is fast and good for English; use small for speed
    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    segments_list, info = model.transcribe(path, beam_size=1, word_timestamps=False)
    segments = []
    full_parts = []
    for s in segments_list:
        seg = {"start": s.start, "end": s.end, "text": s.text.strip()}
        segments.append(seg)
        full_parts.append(s.text.strip())
    full_text = " ".join(full_parts).strip()
    return full_text, segments


def _transcribe_openai_whisper(path: str) -> tuple[str, list[dict]]:
    model = whisper.load_model("base")
    result = model.transcribe(path)
    full_text = result.get("text", "").strip()
    segments = [
        {"start": s["start"], "end": s["end"], "text": s["text"].strip()}
        for s in result.get("segments", [])
    ]
    return full_text, segments
