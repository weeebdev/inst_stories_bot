FROM python:3.10-slim-buster

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for persistent storage
RUN mkdir -p /app/data
RUN mkdir -p /app/data/downloads

# Environment variables
ENV PYTHONUNBUFFERED=1

# Volumes for persistent data
VOLUME /app/data

CMD ["python", "main.py"]
