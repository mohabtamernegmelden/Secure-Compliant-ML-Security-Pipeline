# Multi-stage build to keep size small and secure
FROM python:3.12-slim AS builder

WORKDIR /build

# Install compilation dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies into a wheels directory
RUN pip install --no-cache-dir --user -r requirements.txt


# Final stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/mluser/.local/bin:${PATH}" \
    ENVIRONMENT=production

# Create non-root system group and user
RUN groupadd -g 10001 mlgroup && \
    useradd -u 10001 -g mlgroup -m -s /bin/bash mluser

# Copy wheels/installed libraries from builder stage
COPY --from=builder /root/.local /home/mluser/.local

# Copy application source code
COPY --chown=mluser:mlgroup app/ /app/app/
COPY --chown=mluser:mlgroup models/ /app/models/

# Ensure logs directory exists and is owned by non-root user
RUN mkdir -p /app/logs && chown -m -R mluser:mlgroup /app

# Switch to non-privileged user
USER mluser

# Expose port
EXPOSE 8000

# Health check instructions for container runtime
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start FastAPI application with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--log-level", "info"]
