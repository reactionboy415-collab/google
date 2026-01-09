FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render uses port 10000 by default but we use PORT env variable
EXPOSE 8080

# Script to run both Flask (for health check) and Bot
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} app:app & python bot.py"]