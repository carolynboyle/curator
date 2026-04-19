# go.sh

**Path:** go.sh
**Syntax:** bash
**Generated:** 2026-04-19 14:58:02

```bash
#!/bin/bash
source "$(dirname "$0")/.venv/bin/activate"
uvicorn curator.web.app:app --host 100.64.0.3 --port 8080
```
