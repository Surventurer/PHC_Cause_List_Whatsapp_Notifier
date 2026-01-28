# Lightweight Python image based on Alpine
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Set default timezone
ENV TZ=Asia/Kolkata

# Ensure Python output is sent straight to terminal (e.g. your container logs)
# without being first buffered and that you can see the output of your application (e.g. django logs) in real time.
ENV PYTHONUNBUFFERED=1

# Install uv directly from the official image (avoids pip entirely)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install tzdata for timezone support
RUN apk add --no-cache tzdata

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
