{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python312
    python312Packages.pip
    python312Packages.virtualenv
    gcc-unwrapped
    stdenv.cc.cc.lib
    git
    curl
    lsof
    cloudflared
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    export PYTHONPATH="$PWD"
    export SPECTRA_ENV=development

    # Create venv if needed
    if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      python3.12 -m venv venv
    fi

    # Activate venv
    source venv/bin/activate

    # Install requirements if needed
    if [ ! -f "venv/installed.flag" ]; then
      echo "Installing requirements from requirements.txt..."
      pip install -r requirements.txt
      touch venv/installed.flag
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  SPECTRA — Clinical Decision Support System"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Commands:"
    echo "    devenv up              # Start all services"
    echo "    bash start.sh          # Start API with edge-case handling"
    echo "    START_CLOUDFLARE=true bash start.sh  # + Cloudflare tunnel"
    echo "    python -m backend.export_data        # Generate data"
    echo "    python -m backend.api                # Start API"
    echo ""
    echo "  Local:  http://localhost:8000"
    echo "  Public: https://spectra.alissecretserver.online"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  '';
}
