# Deployment Guide

## Deployment Options

### 1. Local (Development)

```bash
pip install -r requirements.txt
python -m backend.export_data
python -m backend.api
```

Access: http://localhost:8000

### 2. Docker (Recommended for Production)

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m backend.export_data

EXPOSE 8000

CMD ["python", "-m", "backend.api"]
```

**Build and Run:**
```bash
docker build -t spectra-oncology .
docker run -p 8000:8000 spectra-oncology
```

**Docker Compose (with Ollama):**
```yaml
version: '3.8'

services:
  api:
    build: .
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
    entrypoint: >
      sh -c "ollama serve &
             sleep 5 &&
             ollama pull qwen2:7b-instruct-q5_K_M &&
             wait"

volumes:
  ollama:
```

### 3. Cloud (AWS EC2)

```bash
# Launch EC2 (t3.large or larger)
ssh -i key.pem ubuntu@<instance-ip>

sudo apt update && sudo apt install -y python3-pip python3-venv

git clone <repo-url>
cd SPECTRA
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python -m backend.export_data

# Optional: Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2:7b-instruct-q5_K_M
ollama serve &

python -m backend.api &
```

**Security Group:**
- Port 8000 (Application)
- Port 22 (SSH)

### 4. Platform-as-a-Service

**Railway / Render:**
1. Connect GitHub repo
2. Build: `pip install -r requirements.txt && python -m backend.export_data`
3. Start: `python -m backend.api`

**Google Cloud Run:**
```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/spectra', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/spectra']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args: ['run', 'deploy', 'spectra', '--image', 'gcr.io/$PROJECT_ID/spectra', '--platform', 'managed']
```

Note: Cloud Run is stateless — ChromaDB won't persist. Use fallback-only mode or external vector DB.

## Production Checklist

### Before Deployment
- [ ] Run `python -m backend.export_data`
- [ ] Verify `data/knowledge_base.json` exists
- [ ] Verify `data/chroma/` exists
- [ ] Test `/health` endpoint returns 200
- [ ] Test all 4 analysis endpoints
- [ ] Verify `index.html` is in project root

### Security
- [ ] Change `ALLOWED_ORIGINS` from `*` to specific domains
- [ ] Enable HTTPS (Let's Encrypt or similar)
- [ ] Add authentication if needed
- [ ] Disable `/docs` in production if not needed
- [ ] Set up firewall rules

### Performance
- [ ] Use multiple uvicorn workers: `uvicorn backend.api:app --workers 4`
- [ ] Enable HTTP/2 if possible
- [ ] Monitor memory usage (ChromaDB loads into RAM)

### Monitoring
- [ ] Set up health check monitoring (`GET /health`)
- [ ] Monitor Ollama availability
- [ ] Log aggregation (CloudWatch, DataDog, etc.)
- [ ] Set up alerts for failures

## Environment Variables

### Production Settings
```bash
# Required
ALLOWED_ORIGINS=https://yourdomain.com

# Optional
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2:7b-instruct-q5_K_M
LOG_LEVEL=info
```

## Scaling

### Horizontal Scaling
- API is stateless — scale behind load balancer
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

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Knowledge base not loaded | `data/knowledge_base.json` missing | Run `export_data.py` |
| ChromaDB errors | `data/chroma/` missing/corrupted | Delete and re-run `export_data.py` |
| Frontend can't reach API | CORS or network issues | Check `ALLOWED_ORIGINS` |
| Ollama connection refused | Ollama not running | Check `ollama list`, verify `OLLAMA_HOST` |
| Static files not loading | `index.html` missing | Ensure file is in project root |

## Backup

### Files to Backup
- `data/knowledge_base.json` — Can be regenerated
- `data/chroma/` — Vector index (can be rebuilt)
- `models/` — Trained ML models

### Regenerate from Source
```bash
python -m backend.export_data
```

## Health Monitoring

```bash
curl https://yourdomain.com/health
```

Expected response:
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

Key metrics:
- `knowledge_base_loaded` — Must be true
- `chroma_ready` — Must be true
- `ollama_available` — Optional (fallback works without)

## Cost Estimates

| Platform | Instance | Monthly Cost |
|----------|----------|-------------|
| AWS EC2 | t3.large | ~$60 |
| AWS EC2 (no Ollama) | t3.medium | ~$30 |
| Railway | — | ~$5-20 |
| Render | — | ~$7-25 |
| Google Cloud Run | — | ~$0-10 |
