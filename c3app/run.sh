#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 -m uvicorn backend.server:app --port 8000
