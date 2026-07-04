FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy simulator requirements
RUN pip install --no-cache-dir pyzmq

# Copy the simulator codebase
COPY python_simulator /app

# Run the simulator
EXPOSE 7000 7001 7002 7003 8000 8001 8002 8003

CMD ["python", "main.py", "--all"]
