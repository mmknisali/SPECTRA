{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    python311Packages.pip
    python311Packages.virtualenv
    gcc-unwrapped
    stdenv.cc.cc.lib
    git
    curl
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    export PYTHONPATH="$PWD"
    export SPECTRA_ENV=development
    
    # Create venv if needed
    if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      python3.11 -m venv venv
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
    echo "  SPECTRA - Clinical Decision Support System"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Commands:"
    echo "    python -m backend.export_data    # Process data files"
    echo "    python -m backend.api            # Start API + UI"
    echo "    python -m backend.cancer_classifier  # Train ML model"
    echo ""
    echo "  API: http://localhost:8000"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  '';
}
