{ pkgs, ... }:
{
  packages = with pkgs; [
    git
    curl
    python311
    python311Packages.pip
    python311Packages.virtualenv
  ];

  enterShell = ''
    export PYTHONPATH="$PWD"
    export SPECTRA_ENV=development
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  SPECTRA - Clinical Decision Support System"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Quick Start:"
    echo "    1. pip install -r requirements.txt"
    echo "    2. python -m backend.export_data"
    echo "    3. python -m backend.api"
    echo ""
    echo "  API will be available at: http://localhost:8000"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  '';

  processes = {
    # Uncomment to auto-start API on 'devenv up'
    # api.exec = "python -m backend.api";
  };
}
