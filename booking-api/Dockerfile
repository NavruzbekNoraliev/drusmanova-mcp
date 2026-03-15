FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run Alembic migrations then start the server
CMD ["sh", "-c", "python -m alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8089"]
