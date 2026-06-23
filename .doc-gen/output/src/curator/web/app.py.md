# app.py

**Path:** src/curator/web/app.py
**Syntax:** python
**Generated:** 2026-06-23 12:09:21

```python
"""Curator FastAPI application."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from curator.web.routes import landing, crew

app = FastAPI(
    title="Curator",
    description="The Curator — web UI for the Project Crew",
    version="0.2.0",
)

# Mount static files
STATIC_DIR = Path(__file__).parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include routes
app.include_router(landing.router)
app.include_router(crew.router)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}
```
