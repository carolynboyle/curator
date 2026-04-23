#!/bin/bash
# stop.sh - cleanly stop the curator uvicorn server

if pkill -f "uvicorn curator.web.app:app"; then
    echo "Curator stopped."
else
    echo "Curator was not running."
fi
