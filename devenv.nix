{ pkgs, ... }:
{
  packages = with pkgs; [
    git
    curl
  ];

  enterShell = ''
    export PYTHONPATH="$PWD"
    echo "SPECTRA - Oncology Assistant"
    echo "Run: pip install -r requirements.txt"
  '';
}