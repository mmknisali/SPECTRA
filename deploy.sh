#!/bin/bash
# SPECTRA Production Deployment Script
# Usage: ./deploy.sh [environment]

set -e

ENVIRONMENT=${1:-production}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    command -v docker >/dev/null 2>&1 || { error "Docker is required but not installed."; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { error "Docker Compose is required but not installed."; exit 1; }
    
    success "Prerequisites check passed"
}

# Setup environment
setup_env() {
    log "Setting up environment..."
    
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            warning "Created .env from .env.example. Please update it with your values."
        else
            error ".env file not found and .env.example is missing"
            exit 1
        fi
    fi
    
    # Source environment variables
    export $(grep -v '^#' .env | xargs)
    
    success "Environment setup complete"
}

# Database migrations
run_migrations() {
    log "Running database migrations..."
    
    docker-compose -f docker-compose.prod.yml exec -T app alembic upgrade head
    
    success "Migrations complete"
}

# Backup database
backup_database() {
    log "Creating database backup..."
    
    BACKUP_DIR="backups"
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_FILE="$BACKUP_DIR/spectra_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    docker-compose -f docker-compose.prod.yml exec -T db mysqldump \
        -u root -p"${DB_ROOT_PASSWORD}" \
        --single-transaction \
        --routines \
        --triggers \
        "${DB_NAME}" | gzip > "$BACKUP_FILE"
    
    success "Backup created: $BACKUP_FILE"
}

# Deploy application
deploy() {
    log "Starting deployment to $ENVIRONMENT environment..."
    
    check_prerequisites
    setup_env
    
    # Build and start services
    log "Building and starting services..."
    docker-compose -f docker-compose.prod.yml pull
    docker-compose -f docker-compose.prod.yml build --no-cache
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for database
    log "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    run_migrations
    
    # Health check
    log "Performing health check..."
    sleep 5
    
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
            success "Application is healthy"
            break
        fi
        RETRY_COUNT=$((RETRY_COUNT + 1))
        log "Health check attempt $RETRY_COUNT/$MAX_RETRIES..."
        sleep 2
    done
    
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        error "Health check failed after $MAX_RETRIES attempts"
        docker-compose -f docker-compose.prod.yml logs app
        exit 1
    fi
    
    # Cleanup
    log "Cleaning up old Docker images..."
    docker image prune -f
    
    success "Deployment complete!"
    log "Application is running at: https://localhost"
    log "API documentation: https://localhost/docs"
    log "phpMyAdmin: http://localhost:8080"
}

# Rollback to previous version
rollback() {
    log "Rolling back to previous version..."
    
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d
    
    success "Rollback complete"
}

# View logs
logs() {
    docker-compose -f docker-compose.prod.yml logs -f "$@"
}

# Main
 case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    backup)
        backup_database
        ;;
    rollback)
        rollback
        ;;
    logs)
        shift
        logs "$@"
        ;;
    migrate)
        run_migrations
        ;;
    *)
        echo "Usage: $0 {deploy|backup|rollback|logs|migrate}"
        exit 1
        ;;
esac
