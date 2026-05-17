# Deployment Guide

Options for deploying SPECTRA to production.

---

## Deployment Options

### 1. Local Deployment (Single Machine)

Best for: Development, small clinics, demo

**Requirements:**
- Python 3.11+
- 8GB RAM
- Ollama (optional)

**Steps:**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Export data
python -m backend.export_data

# 3. Start API (serves frontend + API on same port)
python -m backend.api
```

**Access:**
- Application (frontend + API): http://localhost:8000
- API docs: http://localhost:8000/docs

---

### 2. Docker Deployment (Recommended)

Best for: Production, reproducible environments

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Export data
RUN python -m backend.export_data

# Expose port
EXPOSE 8000

# Start the API (serves frontend + API)
CMD ["python", "-m", "backend.api"]
```

**Build and Run:**
```bash
# Build image
docker build -t spectra-oncology .

# Run container
docker run -p 8000:8000 spectra-oncology
```

**With Docker Compose:**
```yaml
version: '3.8'

services:
  api:
    build: .
    command: python -m backend.api
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - ALLOWED_ORIGINS=*
    volumes:
      - ./data:/app/data
    depends_on:
      - ollama

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    # Pull model on first run
    entrypoint: >
      sh -c "ollama serve &
             sleep 5 &&
             ollama pull qwen2:7b-instruct-q5_K_M &&
             wait"

volumes:
  ollama:
```

Run with: `docker compose up`

---

### 3. Cloud Deployment

#### AWS EC2

```bash
# 1. Launch EC2 instance (t3.large or larger)
# 2. SSH into instance
ssh -i key.pem ubuntu@<instance-ip>

# 3. Install dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv

# 4. Clone and setup
git clone <repo-url>
cd SPECTRA
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Export data
python -m backend.export_data

# 6. Install and start Ollama (optional)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b-instruct-q5_K_M
ollama serve &

# 7. Start application
python -m backend.api &
```

**Security Group Rules:**
- Port 8000 (Application — serves frontend + API)
- Port 22 (SSH)

#### Google Cloud Run

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/spectra', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/spectra']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args: ['run', 'deploy', 'spectra', '--image', 'gcr.io/$PROJECT_ID/spectra', '--platform', 'managed']
```

**Note:** Cloud Run is stateless — ChromaDB won't persist. Use external ChromaDB or fallback-only mode.

#### Railway / Render

1. Connect GitHub repo
2. Set build command: `pip install -r requirements.txt && python -m backend.export_data`
3. Set start command: `python -m backend.api`

---

### 4. Separate Services Deployment

Best for: Microservices architecture, scaling

**API Service (serves frontend + API):**
```bash
# Environment
export OLLAMA_HOST=http://ollama-internal:11434
export ALLOWED_ORIGINS=https://yourdomain.com

# Run
uvicorn backend.api:app --host 0.0.0.0 --port 8000 --workers 4
```

**Ollama Service:**
```bash
# Run Ollama on separate machine or service
ollama serve
```

**Nginx Reverse Proxy:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Production Checklist

### Before Deployment
- [ ] Run `python -m backend.export_data` to generate KB
- [ ] Verify `data/knowledge_base.json` exists
- [ ] Test `/health` endpoint returns 200
- [ ] Test ICD-10 prediction endpoint
- [ ] Test treatment recommendation endpoint
- [ ] Verify data directory is writable
- [ ] Verify HTML templates are copied correctly (frontend/static/)

### Security
- [ ] Change `ALLOWED_ORIGINS` from `*` to specific domains
- [ ] Enable HTTPS (Let's Encrypt or similar)
- [ ] Add authentication if needed
- [ ] Disable `/docs` in production if not needed
- [ ] Set up firewall rules
- [ ] Set secure cookie and CSRF settings

### Performance
- [ ] Use multiple uvicorn workers: `--workers 4`
- [ ] Enable HTTP/2 if possible
- [ ] Monitor memory usage (ChromaDB loads into RAM)

### Monitoring
- [ ] Set up health check endpoint monitoring
- [ ] Monitor Ollama availability
- [ ] Log aggregation (CloudWatch, DataDog, etc.)
- [ ] Set up alerts for failures

---

## Environment Variables

### Production Settings
```bash
# Required
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Optional
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2:7b-instruct-q5_K_M

# Performance
UVICORN_WORKERS=4
LOG_LEVEL=info
```

---

## Scaling Considerations

### Horizontal Scaling
- API is stateless — can scale behind load balancer
- ChromaDB requires shared storage or external vector DB
- Frontend is served by API; no separate scaling needed

### Without Ollama
- Remove LLM dependency entirely
- Use only fallback protocols (reliable, faster)
- Suitable for high-availability deployments

### With Ollama
- Ollama becomes single point of failure
- Consider GPU instances for faster inference
- Queue requests if multiple users

---

## Troubleshooting

### Issue: "Knowledge base not loaded"
**Cause**: `data/knowledge_base.json` missing
**Fix**: Run `python -m backend.export_data` before deployment

### Issue: ChromaDB errors
**Cause**: `data/chroma/` directory missing or corrupted
**Fix**:
```bash
rm -rf data/chroma
# Re-run will recreate on first query
```

### Issue: Frontend can't reach API
**Cause**: CORS or network issues
**Fix**: Check `ALLOWED_ORIGINS` environment variable

### Issue: Ollama connection refused
**Cause**: Ollama not running or wrong host
**Fix**:
- Check Ollama status: `ollama list`
- Verify `OLLAMA_HOST` environment variable
- Or run without Ollama (fallback mode)

### Issue: Static files not loading
**Cause**: Missing or incorrect template/static paths
**Fix**: Ensure `frontend/` directory is copied into the container or deployment

---

## Backup and Recovery

### Important Files to Backup
- `data/knowledge_base.json` — Can be regenerated
- `data/chroma/` — Vector index (can be rebuilt)
- `models/` — Trained ML models

### Regenerate from Source
If data is lost:
```bash
python -m backend.export_data  # Regenerates KB
# ChromaDB rebuilds automatically on first query
```

---

## Health Monitoring

**Health Endpoint:**
```bash
curl https://yourdomain.com/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "knowledge_base_loaded": true,
  "knowledge_base_size": 20,
  "chroma_ready": true,
  "chroma_documents": 499,
  "ollama_available": true,
  "ollama_models": 1
}
```

**Key Metrics:**
- `knowledge_base_loaded` — Must be true
- `chroma_ready` — Must be true
- `ollama_available` — Optional (fallback works without)

---

## Cost Estimates

### AWS EC2 (t3.large)
- Instance: ~$60/month
- Storage: ~$10/month
- **Total: ~$70/month**

### Without Ollama
- Smaller instance (t3.medium): ~$30/month
- **Total: ~$40/month**

### Managed Services
- Railway: ~$5-20/month depending on usage
- Render: ~$7-25/month depending on tier
- Google Cloud Run: Pay per request (~$0-10/month for low usage)

---

## Next Steps

After deployment:
1. Set up monitoring and alerting
2. Configure backups
3. Document internal procedures
4. Train users on the interface
5. Collect feedback for improvements
