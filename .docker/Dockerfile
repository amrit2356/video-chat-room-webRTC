# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for media processing and WebRTC
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    libssl-dev \
    libffi-dev \
    libopus-dev \
    libvpx-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY templates/ ./templates/
COPY main.py .

# Create necessary directories
RUN mkdir -p sessions recordings

# Set environment variables with defaults
ENV HOST=0.0.0.0
ENV PORT=8080
ENV MAX_USERS_PER_ROOM=5
ENV LOG_LEVEL=INFO
ENV SESSIONS_BASE_PATH=sessions
ENV MAX_FILE_SIZE=104857600
ENV CORS_ORIGINS=*

# Expose the application port
EXPOSE 8080

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# Run the application
CMD ["python", "main.py"]
