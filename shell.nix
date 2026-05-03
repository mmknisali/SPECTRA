{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python311
    python311Packages.pip
    python311Packages.virtualenv
    gcc-unwrapped
    stdenv.cc.cc.lib
  ];

  shellHook = ''
    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
    export PYTHONPATH="$PWD"
    
    # Create venv if needed
    if [ ! -d "venv" ]; then
      echo "Creating virtual environment..."
      python3.11 -m venv venv
    fi
    
    # Activate venv
    source venv/bin/activate
    
    # Install requirements if needed
    if [ ! -f "venv/installed.flag" ]; then
      echo "Installing requirements..."
      pip install pandas openpyxl numpy scikit-learn xgboost joblib transformers peft accelerate bitsandbytes sentence-transformers langchain langchain-community chromadb faiss-cpu fastapi uvicorn streamlit plotly requests python-dotenv pydantic tqdm
      touch venv/installed.flag
    fi
    
    echo "Python: $(python --version)"
    echo "Environment ready!"
  '';
}
