# Multi-stage build for CourseFlow Backend
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project configuration and install Python dependencies
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir --user -e .

# Final stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create data directory for SQLite and ChromaDB
RUN mkdir -p /app/data/chroma

# Set Python path
ENV PYTHONPATH=/app/src

# Expose port (Zeabur will set PORT env var)
ENV PORT=8000
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/v1/health')"

# Start uvicorn with PORT binding
CMD uvicorn courseflow.api.main:app --host 0.0.0.0 --port ${PORT}
