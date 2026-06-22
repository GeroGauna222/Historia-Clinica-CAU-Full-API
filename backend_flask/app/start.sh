#!/bin/bash
set -e

python /app/migrate.py

if [ "$FLASK_ENV" = "production" ]; then
  echo "🚀 Running in PRODUCTION mode (Gunicorn)"
  exec gunicorn \
    --chdir / \
    --pythonpath /app \
    --workers=3 \
    --timeout=120 \
    --bind=0.0.0.0:5000 \
    app.main:app
else
  echo "⚙️ Running in DEVELOPMENT mode (Flask)"
  exec flask run --host=0.0.0.0
fi
