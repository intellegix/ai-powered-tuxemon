# Production Dockerfile for AI-Powered Tuxemon Backend
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for production
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app_user
USER app_user

# Copy application code
COPY --chown=app_user:app_user . .

# Health check for Render
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Expose port (will be overridden by Render)
EXPOSE 8000

# Run application with proper signal handling
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1