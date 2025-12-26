# syntax=docker/dockerfile:1

# ============================================
# Stage 1: Build stage - install dependencies
# ============================================
FROM python:3.13-slim AS builder

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# ============================================
# Stage 2: Runtime stage - minimal final image
# ============================================
FROM python:3.13-slim AS runtime

# Install curl for health checks and clean up apt cache
RUN apt-get update && \
  apt-get install -y --no-install-recommends curl && \
  rm -rf /var/lib/apt/lists/*

# Security: Create non-root user
RUN groupadd --gid 1000 appgroup && \
  useradd --uid 1000 --gid 1000 --shell /bin/false appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY main.py pyproject.toml ./
COPY src/ ./src/

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  # Default port (can be overridden)
  PORT=8000

# Security: Switch to non-root user
USER appuser

# Expose the default port
EXPOSE 8000

# Health check using curl
HEALTHCHECK --interval=120s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:${PORT}/docs || exit 1

# Run the application
CMD ["python", "main.py"]
