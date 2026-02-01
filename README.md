# PrePsych — Therapy Copilot (Hackathon)

Local-first therapy copilot: **Presage** vitals (heart rate, breathing from video) + **Whisper** transcription + **Ollama** for mental-health insights. All processing stays on your machine for privacy.

## What it does

- **Video input**: Use a preset video, upload a file, or record from the browser.
- **Transcription**: Audio is transcribed with Whisper (or faster-whisper).
- **Vitals**: Presage-style metrics (heart rate, breathing). When the iOS app or C++ pipeline feeds data, it’s used; otherwise mock metrics are used for demo.
- **Copilot**: Ollama (local LLM) combines transcript + vitals to suggest short, actionable insights for the therapist (e.g. “Possible discomfort when discussing [topic]; consider gentle follow-up”).
- **Frontend**: Bubbles show each insight; you can check them off when addressed.

## Prerequisites

1. **Ollama** — [install](https://ollama.ai) and run (e.g. `ollama serve`), then pull a model:
   ```bash
   ollama pull llama3.2
   ```
2. **Python 3.10+** — for the backend.
3. **Node 18+** — for the frontend (optional if you only run the API).

## Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip   # avoid old-pip issues on macOS
pip install -r requirements.txt
```

Transcription uses **openai-whisper** by default (no pkg-config needed). For **recorded or uploaded .webm** video you need **ffmpeg** (the backend converts webm to wav for Whisper). Install with `brew install ffmpeg` on macOS, or from [ffmpeg.org](https://ffmpeg.org/download.html). To use faster-whisper instead, install `pkg-config` (e.g. `brew install pkg-config`), then `pip install faster-whisper` and set `USE_FASTER_WHISPER=true` in `backend/.env`.

```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`

### Preset videos

Put sample videos in `backend/preset_videos/` (e.g. `sample.mp4`). They show up in the “Preset video” dropdown.

### Feeding Presage data

Presage (SmartSpectra) runs on the **iOS app** or **C++ pipeline**; there’s no server-side “upload video to Presage” API in this repo. To use real vitals:

1. **Option A**: When you have the iOS app (or C++ app) writing metrics somewhere, POST them to this backend:
   ```bash
   POST /api/presage-metrics
   Body: { "session_id": "<session_id>", "metrics": [ { "pulse_bpm": 72, "breathing_bpm": 14, "timestamp_ms": 0 }, ... ] }
   ```
2. **Option B**: For hackathon demos without live Presage, the app uses **mock** vitals so the copilot still runs.

## Frontend (React + Vite)

From the **project root** (the folder that contains both `backend` and `frontend`):

```bash
cd frontend
npm install
npm run dev
```

If you're in `backend`, use `cd ../frontend` first.

**Installing Node.js (required for frontend):** If `npm` is not found, install Node.js: download the LTS installer from [nodejs.org](https://nodejs.org), or run `brew install node` (Homebrew), or install [nvm](https://github.com/nvm-sh/nvm) then `nvm install --lts`. Restart your terminal after installing.

Open `http://localhost:5173`. The dev server proxies `/api` to `http://localhost:8000`.

- **Preset video**: Choose a file from the dropdown (from `backend/preset_videos/`).
- **Upload**: Pick a video file.
- **Record**: Start/stop recording in the browser (camera + mic).
- Click **“Transcribe & generate insights”** to run Whisper + Ollama and show transcription + copilot bubbles. Check off bubbles when the therapist has addressed them.

## Project layout

```
PrePsych2-1/
├── PrePsych2/              # Xcode app (Presage/SmartSpectra iOS)
├── backend/                 # FastAPI: upload, Whisper, Ollama, Presage metrics
│   ├── app/
│   │   ├── main.py         # Routes
│   │   ├── config.py
│   │   ├── models.py
│   │   └── services/       # transcription, ollama, presage
│   ├── preset_videos/      # Put preset videos here
│   ├── uploads/            # Uploaded/recorded videos (created at runtime)
│   └── requirements.txt
├── frontend/                # React + Vite
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js          # Backend client
│   │   └── ...
│   └── package.json
└── README.md
```

## Environment (optional)

In `backend/` you can add a `.env`:

- `OLLAMA_BASE_URL=http://localhost:11434` — Ollama API (default).
- `USE_FASTER_WHISPER=true` — Use faster-whisper (default); set `false` to use openai-whisper.
- `PRESAGE_API_KEY` — Not used by this backend; the iOS/C++ app uses Presage directly.

## Privacy

- **Ollama**: Models run locally; no transcript or vitals leave your machine.
- **Whisper**: Runs in this backend on your machine (or use faster-whisper); no cloud by default.
- **Presage**: Handled by the iOS/C++ app and Presage’s services; this backend only receives metrics you choose to POST (or uses mock data).

## Info folder note

The “info” folder you mentioned that isn’t getting Presage recording data is likely app-specific (e.g. where the iOS app writes exports). This repo doesn’t read that folder; it expects Presage metrics to be **POSTed** to `/api/presage-metrics` when you wire the app or a script to do so. Until then, mock vitals are used so the copilot still works for the hackathon.
