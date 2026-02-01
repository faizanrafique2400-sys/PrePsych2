#!/usr/bin/env bash
# Run backend (install deps first: pip install -r requirements.txt)
cd "$(dirname "$0")"
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
