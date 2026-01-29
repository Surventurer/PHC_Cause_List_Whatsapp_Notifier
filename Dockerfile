# Debian-based image required for Playwright/Camoufox
FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Set default timezone
ENV TZ=Asia/Kolkata
ENV PYTHONUNBUFFERED=1

# Install uv directly
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system dependencies required for building and basic tools
RUN apt-get update && apt-get install -y \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# We also install playwright browsers and system dependencies here
RUN uv sync --frozen --no-dev

# Install Playwright browsers (Firefox) and their system dependencies
# This is crucial for Camoufox
RUN uv run playwright install --with-deps firefox

# Pre-fetch Camoufox browser binary to bake it into the image
RUN uv run python -m camoufox fetch

# Copy application code
COPY main.py ./

# Create cache directory
RUN mkdir -p cache

# Run the scheduler
CMD ["uv", "run", "main.py"]
