# Lightweight Python image based on Alpine
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install tzdata for timezone support and uv for fast package management
RUN apk add --no-cache tzdata && pip install --no-cache-dir uv

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (faster than pip)
RUN uv sync --frozen --no-dev

# Copy application code
COPY main.py ./

# Create cache directory
RUN mkdir -p cache

# Run the scheduler
CMD ["uv", "run", "main.py"]
