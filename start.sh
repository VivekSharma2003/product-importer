#!/bin/sh
# Start script for Railway deployment
PORT="${PORT:-8000}"
echo "Starting server on port $PORT"
exec gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
