# Quick Deployment to New VM

## 1. From Windows (Git Bash):

```bash
# Create archive excluding build artifacts
cd /c/Users/Parijat/tb_internal

tar -czf documentValidation.tar.gz \
  --exclude='node_modules' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='venv' \
  --exclude='data' \
  documentValidation

# Transfer to VM
scp documentValidation.tar.gz ubuntu@<VM_IP>:~/techbharat/

# Transfer service account credentials separately
scp documentValidation/service-account-credentials.json ubuntu@<VM_IP>:~/techbharat/documentValidation/
```

## 2. On the VM:

```bash
# Extract
cd ~/techbharat
tar -xzf documentValidation.tar.gz
cd documentValidation

# Setup Environment
cp .env.docker.example .env.docker
sed -i 's|VITE_API_BASE_URL=|VITE_API_BASE_URL=http://<VM_IP>:8000|' .env.docker

# Ensure credentials are in place
# mv ../service-account-credentials.json .  (if transferred separately to ~/techbharat)

# Deploy
docker compose -f docker-compose.prod.yml up --build -d

# Verify
docker compose -f docker-compose.prod.yml logs -f
```

## 3. Access:
```
http://<VM_IP>:8000
```

See [DEPLOYMENT_VM.md](./DEPLOYMENT_VM.md) for detailed instructions.
