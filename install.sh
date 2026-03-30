#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Création du venv et installation des dépendances
python3 -m venv "$REPO_DIR/.venv"
source "$REPO_DIR/.venv/bin/activate"
pip install -r "$REPO_DIR/requirements.txt"

# Création du wrapper ~/.local/bin/tplinkreport
mkdir -p ~/.local/bin
cat > ~/.local/bin/tplinkreport << EOF
#!/bin/bash
cd $REPO_DIR
source .venv/bin/activate
python3 report.py
EOF
chmod +x ~/.local/bin/tplinkreport

# Création du lanceur GNOME
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/tplinkreport.desktop << EOF
[Desktop Entry]
Name=TPLink Report
Comment=Génère le rapport réseau
Exec=bash -c '~/.local/bin/tplinkreport'
Icon=network-workgroup
Terminal=true
Type=Application
Categories=Network;
EOF

echo "Installation terminée"