FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# flickr8k parquet data and the sqlite data dir are mounted as volumes (see docker-compose.yml)
ENV PARQUET_DIR=/data/flickr8k
ENV DB_PATH=/data/db/flickr8k.db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
