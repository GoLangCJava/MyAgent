#!/bin/bash
set -e
echo "Init Deep Platform..."
cp -n .env.template .env 2>/dev/null || true
echo "Run: docker compose up --build -d"
echo "Frontend: http://localhost:5173  admin/admin123"
echo "Backend docs: http://localhost:8000/docs"
echo "Ready: http://localhost:8000/api/system/ready"
