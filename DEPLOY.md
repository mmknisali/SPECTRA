# SPECTRA - Production Deployment Guide

## Quick Demo (30-90 seconds)

1. **Open demo.html** - Pre-loaded with sample patients
2. **Click a patient card** - Instantly loads history
3. **Click "AI Analizi Başlat"** - View AI recommendations

## Production Deployment

### Prerequisites
- Docker & Docker Compose
- SSL certificates (for HTTPS)
- Vast.ai instance (or any cloud provider)

### 1. Clone & Configure

```bash
git clone https://github.com/mmknisali/SPECTRA.git
cd SPECTRA

# Copy environment file
cp .env.production .env

# Edit .env with your values
nano .env
```

Required changes in `.env`:
- `SECRET_KEY` - Generate with `openssl rand -hex 32`
- `DB_PASSWORD` and `DB_ROOT_PASSWORD` - Secure passwords
- `ALLOWED_ORIGINS` - Your domain(s)

### 2. Deploy Locally

```bash
# Start all services
./deploy.sh deploy

# Or manually:
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

Access:
- Application: https://localhost
- API Docs: https://localhost/docs
- phpMyAdmin: http://localhost:8080

### 3. GitHub Actions Auto-Deploy to Vast.ai

1. **Add GitHub Secrets** (Settings → Secrets → Actions):
   ```
   VAST_HOST=your.vast.ai.ip
   VAST_SSH_PORT=your_ssh_port
   VAST_USER=root
   VAST_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----
   DB_ROOT_PASSWORD=your_secure_password
   ```

2. **Push to main branch** - Auto-deploys:
   ```bash
   git add .
   git commit -m "feat: production ready"
   git push origin main
   ```

### 4. SSL Certificates

Place certificates in `deploy/ssl/`:
```bash
mkdir -p deploy/ssl
cp your-cert.pem deploy/ssl/cert.pem
cp your-key.pem deploy/ssl/key.pem
```

Or use Let's Encrypt:
```bash
certbot certonly --standalone -d yourdomain.com
```

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Backup & Restore

```bash
# Create backup
./deploy.sh backup

# Or manually:
docker exec spectra_db mysqldump -u root -p spectra_db > backup.sql

# Restore
docker exec -i spectra_db mysql -u root -p spectra_db < backup.sql
```

## Monitoring

Health checks:
```bash
curl https://yourdomain.com/health
```

View logs:
```bash
./deploy.sh logs

# Specific service
./deploy.sh logs app
```

## Security Checklist

- [ ] Changed all default passwords
- [ ] Generated secure SECRET_KEY
- [ ] Enabled HTTPS with valid SSL
- [ ] Set ALLOWED_ORIGINS (not *)
- [ ] Disabled DEBUG mode
- [ ] Configured firewall rules
- [ ] Enabled automatic backups
- [ ] Set up monitoring/alerting

## Troubleshooting

### Database connection fails
```bash
# Check if DB is healthy
docker-compose -f docker-compose.prod.yml ps

# View DB logs
docker-compose -f docker-compose.prod.yml logs db
```

### Migrations fail
```bash
# Reset and re-run
docker-compose -f docker-compose.prod.yml exec app alembic downgrade base
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### Ollama not responding
```bash
# Check GPU availability
docker exec spectra_ollama ollama list

# Pull model manually
docker exec spectra_ollama ollama pull qwen2:7b-instruct-q5_K_M
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│  FastAPI    │────▶│   MySQL     │
│  (SSL/HTTP) │     │   (App)     │     │  (Database) │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Ollama    │
                    │    (LLM)    │
                    └─────────────┘
```

## Support

- GitHub Issues: https://github.com/mmknisali/SPECTRA/issues
- API Docs: https://yourdomain.com/docs
