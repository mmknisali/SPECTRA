# Deployment Guide

## Table of Contents

1. [Local Deployment](#local-deployment)
2. [Homelab Deployment](#homelab-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Docker Deployment](#docker-deployment)
5. [Cloudflare Tunnel](#cloudflare-tunnel)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Local Deployment

### Prerequisites

- Python 3.11+
- 8GB RAM
- 4GB VRAM (optional, for LLM inference)

### Steps

```bash
# 1. Clone or download the project
cd /path/to/spectra

# 2. Install dependencies
pip install -r requirements.txt

# 3. Process data
python -m backend.export_data

# 4. Train models
python -m backend.cancer_classifier

# 5. Start API (Terminal 1)
python -m backend.api

# 6. Start UI (Terminal 2)
streamlit run frontend/app.py
```

### Accessing the Application

- API: http://localhost:8000
- UI: http://localhost:8501
- API Docs: http://localhost:8000/docs

---

## Homelab Deployment

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB |
| VRAM | 4GB | 8GB |
| Storage | 10GB | 50GB |
| Network | 10Mbps | 100Mbps |

### Installation Steps

#### 1. Prepare the System

```bash
# Check system resources
free -h
nvidia-smi  # if available
df -h
```

#### 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install -y python3.11 python3.11-venv python3-pip

# Create project directory
sudo mkdir -p /opt/spectra
sudo chown $USER:$USER /opt/spectra
git clone <repo> /opt/spectra
```

#### 3. Create Virtual Environment

```bash
cd /opt/spectra
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Train Models

```bash
python -m backend.export_data
python -m backend.cancer_classifier
```

#### 5. Create Systemd Services

```bash
# Create API service
sudo tee /etc/systemd/system/spectra-api.service > /dev/null <<EOF
[Unit]
Description=SPECTRA API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/spectra
ExecStart=/opt/spectra/venv/bin/python -m backend.api
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create UI service
sudo tee /etc/systemd/system/spectra-ui.service > /dev/null <<EOF
[Unit]
Description=SPECTRA UI
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/spectra
ExecStart=/opt/spectra/venv/bin/streamlit run frontend/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable spectra-api spectra-ui
sudo systemctl start spectra-api spectra-ui
```

#### 6. Verify Services

```bash
# Check service status
sudo systemctl status spectra-api
sudo systemctl status spectra-ui

# Check logs
sudo journalctl -u spectra-api -f
sudo journalctl -u spectra-ui -f
```

---

## Cloud Deployment

### Using Cloud GPU (vast.ai)

#### 1. Rent GPU

```bash
# Search for available GPUs
vastai search gpu "RTX 3090"

# Rent GPU
vastai rent gpu --gpu RTX-3090 --duration 2:0:0
```

#### 2. Train Model

```bash
# SSH into instance
vastai ssh <instance_id>

# Install dependencies
pip install -r requirements.txt

# Train LoRA
accelerate launch train.py --model Qwen/Qwen2-1.8B --use_lora
```

#### 3. Download Model

```bash
# Download LoRA adapter
scp user@instance:/path/to/lora_adapter ./models/
```

---

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 8000 8501

# Run application
CMD ["python", "-m", "backend.api"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000

  ui:
    build: .
    command: streamlit run frontend/app.py
    ports:
      - "8501:8501"
    depends_on:
      - api
    environment:
      - API_BASE=http://api:8000
```

### Build and Run

```bash
# Build images
docker-compose build

# Run services
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## Cloudflare Tunnel

### Why Cloudflare Tunnel?

- No static IP needed
- Free
- Secure
- Easy setup

### Setup Steps

#### 1. Install Cloudflare Tunnel

```bash
# Download and install
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared
```

#### 2. Authenticate

```bash
cloudflare tunnel login
```

#### 3. Create Tunnel

```bash
cloudflare tunnel create spectra
```

#### 4. Configure Tunnel

```bash
# Add route for API
cloudflare tunnel route dns spectra api.spectra.example.com

# Add route for UI
cloudflare tunnel route dns spectra app.spectra.example.com
```

#### 5. Run Tunnel

```bash
# Run as service
cloudflare tunnel --protocol http2 --port 8501 serve http://localhost:8501
```

### Alternative: Argo Tunnel

```bash
# Create Argo tunnel
argo tunnel create spectra

# Set up DNS
argo tunnel dns add spectra example.com app.spectra.example.com
```

---

## Monitoring

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","models_loaded":true,"knowledge_base_size":20}
```

### Logs

#### Systemd Logs

```bash
# View API logs
sudo journalctl -u spectra-api -f

# View UI logs
sudo journalctl -u spectra-ui -f
```

#### Docker Logs

```bash
docker-compose logs -f api
docker-compose logs -f ui
```

### Resource Monitoring

```bash
# CPU usage
top -bn1 | grep python

# Memory usage
free -h

# Disk usage
df -h
```

---

## Troubleshooting

### API Not Starting

```bash
# Check port
lsof -i :8000

# Check logs
tail -f /var/log/spectra/api.log
```

### UI Not Loading

```bash
# Check API is running
curl http://localhost:8000/health

# Restart UI
sudo systemctl restart spectra-ui
```

### Out of Memory

```bash
# Clear cache
sync && echo 3 > /proc/sys/vm/drop_caches

# Check memory
free -h
```

### Model Not Found

```bash
# Check models directory
ls -la /opt/spectra/models/

# Re-train if needed
python -m backend.cancer_classifier
```

---

## Backup and Restore

### Backup

```bash
# Backup models
tar -czvf spectra-models-backup.tar.gz models/

# Backup data
tar -czvf spectra-data-backup.tar.gz data/
```

### Restore

```bash
# Restore models
tar -xzvf spectra-models-backup.tar.gz

# Restore data
tar -xzvf spectra-data-backup.tar.gz
```

---

## Security Considerations

### Firewall

```bash
# Allow specific ports
sudo ufw allow 8000/tcp
sudo ufw allow 8501/tcp
sudo ufw enable
```

### SSL/TLS

```bash
# Using Cloudflare (recommended)
# Or using self-signed cert
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365
```

---

## Next Steps

- [ ] Set up automatic updates
- [ ] Implement backup automation
- [ ] Add monitoring (Prometheus/Grafana)
- [ ] Set up CI/CD pipeline