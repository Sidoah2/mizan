FROM python:3.11-slim

# Install system dependencies & Node.js
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose ports
EXPOSE 3000

# Environment variables
ENV PORT=3000
ENV PYTHONUNBUFFERED=1

# Start Python FastAPI backend in background and Node server in foreground
CMD ["sh", "-c", "python -m uvicorn syncra_engine.server:app --host 127.0.0.1 --port 8000 & node server.js"]
