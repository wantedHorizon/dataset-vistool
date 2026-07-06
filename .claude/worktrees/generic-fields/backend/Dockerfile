FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# The datasets root, fields.json, and the sqlite data dir are mounted as
# volumes (see docker-compose.yml); the dataset name comes from fields.json.
ENV PARQUET_ROOT=/data/datasets
ENV DB_DIR=/data/db
ENV FIELDS_PATH=/app/fields.json

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
