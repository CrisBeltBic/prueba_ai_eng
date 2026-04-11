FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8084"]
