# Multi-stage build for surah-splitter FastAPI application
# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install system dependencies for audio processing and building
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files and source code
COPY pyproject.toml README.md ./
COPY src ./src

# Create virtual environment and install dependencies using uv
RUN uv venv .venv
# Activate venv and install dependencies into it
RUN . .venv/bin/activate && uv pip install -e .

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgomp1 \
    curl \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser templates/ ./templates/
COPY --chown=appuser:appuser static/ ./static/
COPY --chown=appuser:appuser data/ ./data/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:${PYTHONPATH}"
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR="/home/appuser/.config/matplotlib"
ENV HF_HOME="/home/appuser/.cache/huggingface"

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/cache /app/uploads /home/appuser/.cache /home/appuser/.config && \
    chown -R appuser:appuser /app/logs /app/cache /app/uploads /home/appuser

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health', timeout=5)" || exit 1

# Default command to run the application
CMD ["uvicorn", "src.surah_splitter.api.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]