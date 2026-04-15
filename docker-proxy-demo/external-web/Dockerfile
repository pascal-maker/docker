ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

ARG APP_PORT=5050

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE ${APP_PORT}

CMD ["python", "app.py"]
