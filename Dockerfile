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

# Copy application code
COPY backend ./backend
COPY infrastructure ./infrastructure

ENV ENVIRONMENT=staging
ENV API_HOST=0.0.0.0
ENV API_PORT=8001
ENV DATABASE_URL=sqlite:///./enterprise_multi_agent.db
ENV ALLOW_DEMO_AUTH=true

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD curl -f http://127.0.0.1:8001/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
