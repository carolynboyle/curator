#!/bin/bash
source "$(dirname "$0")/.venv/bin/activate"
uvicorn curator.web.app:app --host localhost --port 8080 --reload
