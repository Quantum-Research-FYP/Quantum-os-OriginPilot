#!/bin/bash
set -e

DEPLOY_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DEPLOY_DIR"

echo "=============================================="
echo "  PilotOS v4.2 — Full Deployment Script"
echo "=============================================="
echo "Working directory: $DEPLOY_DIR"
echo ""

# ── Step 1: Start MySQL & MongoDB via Docker ──
echo "── Step 1: Starting MySQL & MongoDB (Docker) ──"

# MySQL
if docker ps --format '{{.Names}}' | grep -q '^pilotos-mysql$'; then
    echo "✓ MySQL container already running"
else
    echo "Starting MySQL container..."
    docker rm -f pilotos-mysql 2>/dev/null || true
    docker run -d \
        --name pilotos-mysql \
        -e MYSQL_ROOT_PASSWORD=root123 \
        -e MYSQL_DATABASE=PilotOS_DB \
        -p 3306:3306 \
        --restart unless-stopped \
        mysql:8.0
    echo "Waiting for MySQL to be ready..."
    sleep 15
    echo "✓ MySQL started on port 3306"
fi

# MongoDB
if docker ps --format '{{.Names}}' | grep -q '^pilotos-mongodb$'; then
    echo "✓ MongoDB container already running"
else
    echo "Starting MongoDB container..."
    docker rm -f pilotos-mongodb 2>/dev/null || true
    docker run -d \
        --name pilotos-mongodb \
        -e MONGO_INITDB_DATABASE=PilotOS_DB \
        -p 27017:27017 \
        --restart unless-stopped \
        mongo:7.0
    echo "Waiting for MongoDB to be ready..."
    sleep 10
    echo "✓ MongoDB started on port 27017"
fi

echo ""

# ── Step 2: Setup Python venv & install deps ──
echo "── Step 2: Setting up Python virtual environment ──"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Created virtual environment"
fi
source venv/bin/activate
pip install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# ── Step 3: Load PilotOS Docker image ──
echo "── Step 3: Loading PilotOS Docker image (~2.5 GB) ──"
if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q '^pilotos:4.2$'; then
    echo "✓ PilotOS image already loaded"
else
    echo "Loading pilotos:4.2.iso (this may take a few minutes)..."
    docker load -i "pilotos:4.2.iso"
    echo "✓ PilotOS Docker image loaded"
fi
echo ""

# ── Step 4: Initialize database ──
echo "── Step 4: Initializing database ──"
python3 AutoDeploy.py initDB
echo "✓ Database initialized"
echo ""

# ── Step 5: Start PilotOS services ──
echo "── Step 5: Starting PilotOS services ──"
python3 AutoDeploy.py start
echo ""

echo "=============================================="
echo "  Deployment Complete!"
echo "=============================================="
echo ""
echo "  PilotOS API:      http://localhost:10010"
echo "  Management UI:    http://localhost:10021"
echo "  Internal API:     http://localhost:10020"
echo ""
