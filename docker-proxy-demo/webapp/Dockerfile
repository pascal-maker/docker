ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim

ARG APP_PORT=5000

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY templates templates/

EXPOSE ${APP_PORT}

# Run the application
CMD ["python", "app.py"]
