{ pkgs, ... }:
{
  packages = with pkgs; [
    git
    curl
    jq
    python311
    python311Packages.pip
    python311Packages.virtualenv
    gcc-unwrapped
    stdenv.cc.cc.lib
  ];

  enterShell = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    export PYTHONPATH="$PWD"

    # Create venv if it doesn't exist
    if [ ! -d "venv" ]; then
      echo "Creating Python virtual environment..."
      python3.11 -m venv venv
      source venv/bin/activate
      pip install -r requirements.txt
    else
      source venv/bin/activate
    fi

    echo ""
    echo "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
    echo "┃  SPECTRA - Oncology Assistant             ┃"
    echo "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    echo ""
    echo "Python: $(python --version)"
    echo ""
    echo "Commands:"
    echo " python -m backend.export_data → Process data"
    echo " python -m backend.cancer_classifier → Train XGBoost"
    echo " python -m backend.api → Start API"
    echo " streamlit run frontend/app.py → Start UI"
    echo ""
  '';
}