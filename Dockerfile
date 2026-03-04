
# =============================================================================
# Doc Refinery Agent - Dockerfile
# Production-ready container for document intelligence pipeline
# =============================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY tests/ ./tests/
COPY main.py demo.py ./
COPY rubric/ ./rubric/
COPY .refinery/extraction_ledger.jsonl ./.refinery/ 2>/dev/null || true

# Install dependencies
RUN uv sync --frozen

# Create data directory
RUN mkdir -p data .refinery

# Expose port for API (if needed)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "from src.agents.triage import TriageAgent; TriageAgent()" || exit 1

# Default command
CMD ["uv", "run", "python", "demo.py"]

# =============================================================================
# Usage:
#   docker build -t doc-refinery-agent .
#   docker run -v ./data:/app/data doc-refinery-agent
# =============================================================================