#!/usr/bin/env bash
# SPECTRA Startup Script
# Handles all edge cases: data generation, Ollama detection, port conflicts, etc.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
check_python() {
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    else
        log_error "Python not found. Install Python 3.11+ first."
        exit 1
    fi
    local version=$($PYTHON -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    log_ok "Python $version found"
}

check_venv() {
    if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        log_ok "Virtual environment activated"
    else
        log_warn "No virtual environment found. Run: python3 -m venv venv && source venv/bin/activate"
        exit 1
    fi
}

check_pythonpath() {
    if [[ "${PYTHONPATH:-}" != *"$PWD"* ]]; then
        export PYTHONPATH="$PWD:${PYTHONPATH:-}"
        log_info "Set PYTHONPATH=$PWD"
    fi
}

check_dependencies() {
    local missing=()
    for pkg in fastapi pandas chromadb pydantic requests; do
        if ! $PYTHON -c "import $pkg" 2>/dev/null; then
            missing+=("$pkg")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_warn "Missing packages: ${missing[*]}"
        log_info "Installing dependencies..."
        pip install -r requirements.txt -q
        log_ok "Dependencies installed"
    else
        log_ok "All Python dependencies available"
    fi
}

check_dataset() {
    local found=""
    if [ -f "hackathon_veri.csv" ]; then
        found="hackathon_veri.csv"
    elif [ -f "datamedx_veriset_26.xlsx" ]; then
        found="datamedx_veriset_26.xlsx"
    fi

    if [ -z "$found" ]; then
        log_error "No dataset found. Place hackathon_veri.csv or datamedx_veriset_26.xlsx in the project root."
        exit 1
    fi
    log_ok "Dataset found: $found"
}

check_data_dir() {
    if [ -d "data" ] && [ -f "data/knowledge_base.json" ] && [ -d "data/chroma" ]; then
        log_ok "Data directory ready (knowledge base + ChromaDB)"
        return 0
    fi

    log_warn "Data not generated yet. Running export_data.py (this may take a few minutes)..."
    $PYTHON -m backend.export_data
    if [ $? -eq 0 ]; then
        log_ok "Data generated successfully"
    else
        log_error "Data export failed. Check the error messages above."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Ollama detection and setup
# ---------------------------------------------------------------------------
check_ollama() {
    OLLAMA_AVAILABLE=false
    OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
    OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2:7b-instruct-q5_K_M}"

    # Check if Ollama is already running
    if curl -s --max-time 2 "$OLLAMA_HOST/api/tags" &>/dev/null; then
        OLLAMA_AVAILABLE=true
        log_ok "Ollama is already running at $OLLAMA_HOST"

        # Check if model is available
        if curl -s "$OLLAMA_HOST/api/tags" | $PYTHON -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
sys.exit(0 if any('$OLLAMA_MODEL' in m for m in models) else 1)
" 2>/dev/null; then
            log_ok "Model $OLLAMA_MODEL is available"
        else
            log_warn "Model $OLLAMA_MODEL not found. Pulling it (this may take a while)..."
            ollama pull "$OLLAMA_MODEL" 2>/dev/null || log_warn "Could not pull model. Will use fallback mode."
        fi
        return 0
    fi

    # Check if Ollama binary exists
    if command -v ollama &>/dev/null; then
        log_info "Ollama binary found but not running. Starting it..."
        ollama serve &>/dev/null &
        OLLAMA_PID=$!
        sleep 3

        if curl -s --max-time 2 "$OLLAMA_HOST/api/tags" &>/dev/null; then
            OLLAMA_AVAILABLE=true
            log_ok "Ollama started successfully"

            # Pull model if needed
            if ! curl -s "$OLLAMA_HOST/api/tags" | $PYTHON -c "
import sys, json
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
sys.exit(0 if any('$OLLAMA_MODEL' in m for m in models) else 1)
" 2>/dev/null; then
                log_warn "Pulling model $OLLAMA_MODEL (this may take a while)..."
                ollama pull "$OLLAMA_MODEL" 2>/dev/null || log_warn "Could not pull model. Will use fallback mode."
            fi
        else
            log_warn "Could not start Ollama. Will use fallback mode."
        fi
    else
        log_warn "Ollama not installed. Will use fallback mode (rule-based analysis)."
        log_info "To enable AI-powered analysis: curl -fsSL https://ollama.ai/install.sh | sh"
    fi
}

# ---------------------------------------------------------------------------
# Port checks
# ---------------------------------------------------------------------------
check_port() {
    local port=$1
    local name=$2
    if lsof -Pi :$port -sTCP:LISTEN -t &>/dev/null 2>&1 || ss -tlnp | grep -q ":$port "; then
        log_error "Port $port is already in use. Stop the process using it and try again."
        log_info "Find the process: lsof -i :$port"
        return 1
    fi
    log_ok "Port $port is available ($name)"
    return 0
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  SPECTRA — Clinical Decision Support System"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    log_info "Running pre-flight checks..."
    echo ""

    check_python
    check_venv
    check_pythonpath
    check_dependencies
    check_dataset
    check_data_dir
    echo ""

    log_info "Checking Ollama..."
    check_ollama
    echo ""

    log_info "Checking ports..."
    check_port 8000 "SPECTRA API" || exit 1
    if [ "$OLLAMA_AVAILABLE" = true ]; then
        check_port 11434 "Ollama" 2>/dev/null || true
    fi
    echo ""

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Starting SPECTRA API on http://localhost:8000"
    if [ "$OLLAMA_AVAILABLE" = true ]; then
        echo "  Mode: RAG + LLM (AI-powered)"
    else
        echo "  Mode: Fallback (rule-based)"
    fi
    echo "  Press Ctrl+C to stop"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # Start the API
    exec $PYTHON -m backend.api
}

main "$@"
