# DocumentValidation - VM Deployment Guide

## Prerequisites on Target VM
- Docker and Docker Compose installed
- Ubuntu/Linux system with user privileges
- Outbound access to NeonDB (ports 5432) and Google Cloud APIs

## Deployment Steps

### 1. Transfer Code to VM

From your local machine (Git Bash on Windows):

```bash
# Using tar to exclude unnecessary files
cd /c/Users/Parijat/tb_internal

tar -czf documentValidation.tar.gz \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='venv' \
  --exclude='data' \
  --exclude='logs' \
  --exclude='service-account-credentials.json' \
  documentValidation

# Transfer to VM
scp documentValidation.tar.gz ubuntu@<VM_IP>:~/techbharat/

# Transfer service account credentials separately
scp documentValidation/service-account-credentials.json ubuntu@<VM_IP>:~/techbharat/documentValidation/

# SSH in and extract
ssh ubuntu@<VM_IP>
cd ~/techbharat
tar -xzf documentValidation.tar.gz
rm documentValidation.tar.gz
```

### 2. Setup Environment Variables

```bash
cd ~/techbharat/documentValidation

# Ensure .env.docker is setup
# If you didn't transfer it (it's in the tar if not ignored):
cp .env.docker.example .env.docker

# IMPORTANT: Update the API Base URL to your VM's IP
sed -i 's|VITE_API_BASE_URL=|VITE_API_BASE_URL=http://<VM_IP>:8000|' .env.docker
# Or edit manually: nano .env.docker
```

**Configuration Notes:**
- `DATABASE_URL`: Ensure it points to the correct NeonDB instance.
- `VITE_API_BASE_URL`: Must point to `http://<VM_IP>:8000` for frontend to reach backend.

### 3. Deploy with Docker Compose

```bash
cd ~/techbharat/documentValidation

# Build and start
# Note: We use docker-compose.prod.yml specifically
docker compose -f docker-compose.prod.yml up --build -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

### 4. Verify Deployment

```bash
# Check if containers are running
docker ps

# Test the endpoint
curl http://localhost:8000

# Access from browser
http://<VM_IP>:8000
```

## Quick Commands Reference

### Stop the application
```bash
docker compose -f docker-compose.prod.yml down
```

### Restart the application
```bash
docker compose -f docker-compose.prod.yml restart
```

### View logs
```bash
docker compose -f docker-compose.prod.yml logs -f
```

### Rebuild after code changes
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

## Port Configuration
- **Frontend**: Port 8000 (mapped to host)
- **Backend**: Internal only (proxied by frontend)
