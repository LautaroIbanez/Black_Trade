#!/bin/bash
# Entrypoint script for Black Trade backend
set -e

echo "Starting Black Trade backend initialization..."

# Run database migrations
echo "Running database migrations..."
python backend/db/init_db.py

# Start the backend
echo "Starting backend server..."
exec uvicorn backend.app:app --host 0.0.0.0 --port 8000




