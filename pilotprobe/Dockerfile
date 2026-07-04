FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir \
    pyzmq \
    fastapi \
    uvicorn \
    jsonschema \
    aiosqlite \
    click

# Copy the codebase
COPY . /app

# Expose proxy ports, pub ports, and dashboard
EXPOSE 6000 6001 6002 6003 9000 9001 9002 9003 9090

# Default environment variables
ENV SIMULATOR_HOST=simulators

# Run the proxy & dashboard server
CMD ["python", "main.py", "--proxy", "--dashboard"]
