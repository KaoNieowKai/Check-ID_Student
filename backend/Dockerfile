# ─────────────────────────────────────────────────────────────────────────────
# Dockerfile for Student Activity Attendance Management WebApp
# Target: Render Web Service (stateless, single-container)
# ─────────────────────────────────────────────────────────────────────────────

# Use the same Python major version as the local development environment
FROM python:3.13-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr immediately
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Cloud Run injects PORT; default to 8080 if not set
ENV PORT=8080

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set working directory — mirrors the project's backend/ folder structure
WORKDIR /app

# Install system dependencies required by psycopg2-binary and Pillow (used by qrcode)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer cache optimisation — only rebuilt if deps change)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application source code
# .dockerignore ensures .env, venv, attendance.db, __pycache__ etc. are excluded
COPY . .

# Switch to non-root user
RUN chown -R appuser:appgroup /app
USER appuser

# Expose the port (documentation only — Render injects $PORT at runtime)
EXPOSE 8080

# Start the application using uvicorn, binding to Render's injected $PORT
# --workers 1 ensures the in-memory WebSocket ConnectionManager is not split across processes
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
