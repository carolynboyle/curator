#!/bin/bash
source "$(dirname "$0")/.venv/bin/activate"
uvicorn curator.web.app:app --host 100.64.0.3 --port 8080