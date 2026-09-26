#!/usr/bin/env bash
set -e

echo "=== Building frontend ==="
cd frontend
npm ci
npm run build
cd ..

echo "=== Frontend dist contents ==="
ls -la frontend/dist/

echo "=== Build complete ==="
