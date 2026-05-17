{ pkgs, ... }:

{
  packages = with pkgs; [
    git
    curl
    python311
    python311Packages.pip
    python311Packages.virtualenv
    lsof
    cloudflared
  ];

  # Processes for `devenv up`
  processes = {
    # Ollama LLM service (optional - system works without it)
    ollama = {
      exec = ''
        if command -v ollama &>/dev/null; then
          echo "[ollama] Starting Ollama server..."
          ollama serve
        else
          echo "[ollama] Ollama not installed. Skipping."
          echo "[ollama] Install: curl -fsSL https://ollama.ai/install.sh | sh"
          # Keep process alive so devenv up doesn't exit
          tail -f /dev/null
        fi
      '';
    };

    # SPECTRA API (serves frontend + API on port 8000)
    api = {
      exec = ''
        export PYTHONPATH="$PWD"

        # Activate venv if exists
        if [ -d "venv" ]; then
          source venv/bin/activate
        fi

        # Check for dataset
        if [ ! -f "hackathon_veri.csv" ] && [ ! -f "datamedx_veriset_26.xlsx" ]; then
          echo "[api] ERROR: No dataset found. Place hackathon_veri.csv or datamedx_veriset_26.xlsx in project root."
          exit 1
        fi

        # Generate data if not exists
        if [ ! -f "data/knowledge_base.json" ] || [ ! -d "data/chroma" ]; then
          echo "[api] Data not found. Running export_data.py..."
          python -m backend.export_data
        fi

        # Check Ollama availability
        if curl -s --max-time 2 http://localhost:11434/api/tags &>/dev/null; then
          echo "[api] Ollama detected — using RAG + LLM mode"
        else
          echo "[api] Ollama not available — using fallback mode (rule-based)"
        fi

        echo "[api] Starting SPECTRA API on http://localhost:8000"
        exec python -m backend.api
      '';
    };

    # Cloudflare Tunnel (exposes API to the internet)
    cloudflare = {
      exec = ''
        CONFIG_FILE="$PWD/cloudflared/config.yml"

        if [ ! -f "$CONFIG_FILE" ]; then
          echo "[cloudflare] Config not found at $CONFIG_FILE. Skipping."
          tail -f /dev/null
          exit 0
        fi

        # Wait for API to be ready
        echo "[cloudflare] Waiting for SPECTRA API on port 8000..."
        for i in $(seq 1 30); do
          if curl -s --max-time 1 http://localhost:8000/health &>/dev/null; then
            echo "[cloudflare] API is ready"
            break
          fi
          if [ $i -eq 30 ]; then
            echo "[cloudflare] API did not start within 30s. Starting tunnel anyway..."
          fi
          sleep 1
        done

        echo "[cloudflare] Starting Cloudflare Tunnel..."
        echo "[cloudflare] Public URL: https://spectra.alissecretserver.online"
        exec cloudflared tunnel --config "$CONFIG_FILE" run
      '';
    };
  };

  enterShell = ''
    export PYTHONPATH="$PWD"
    export SPECTRA_ENV=development

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  SPECTRA — Clinical Decision Support System"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Quick Start:"
    echo "    devenv up              # Start all services"
    echo "    bash start.sh          # Start API with edge-case handling"
    echo ""
    echo "  Manual:"
    echo "    python -m backend.export_data  # Generate data"
    echo "    python -m backend.api          # Start API"
    echo ""
    echo "  Local:  http://localhost:8000"
    echo "  Public: https://spectra.alissecretserver.online"
    echo "  Docs:   http://localhost:8000/docs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  '';
}
