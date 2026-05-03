FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run both web and worker processes
CMD gunicorn app.webhook:app --worker-class sync --bind 0.0.0.0:$PORT & python worker.py
