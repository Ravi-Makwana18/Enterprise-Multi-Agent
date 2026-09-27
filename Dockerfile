# Stage 1: Build Frontend Assets
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Runtime Backend & App Server
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and built frontend
COPY backend ./backend
COPY infrastructure ./infrastructure
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV ENVIRONMENT=production
ENV API_HOST=0.0.0.0
ENV PORT=8001
ENV DATABASE_URL=sqlite:///./enterprise_multi_agent.db
ENV ALLOW_DEMO_AUTH=true

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD curl -f http://127.0.0.1:${PORT:-8001}/health || exit 1

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
