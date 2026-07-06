FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Registry, downloaded datasets, and SQLite DBs live under /app/data (mounted volume)
ENV PARQUET_DIR=/data/parquet

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
