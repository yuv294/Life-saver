FROM python:3.11-slim

# System deps for asyncpg (libpq) and OR-Tools (libgomp)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

# Cloud Run requires PORT env var — default 8080
ENV PORT=8080
EXPOSE 8080

# Run with Uvicorn; workers=1 keeps Cloud Run cost low on free tier
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--log-level", "info"]
