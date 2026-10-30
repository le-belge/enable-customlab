#!/bin/bash
# Double-cliquez pour lancer e-NABLE CustomLab (macOS). Aucune ligne de commande nécessaire.
cd "$(dirname "$0")" || exit 1
if [ ! -x ".venv/bin/python" ]; then
  osascript -e 'display alert "CustomLab" message "Environnement Python introuvable (.venv). Voir README.md pour l'"'"'installation." as critical' 2>/dev/null
  echo "Environnement .venv introuvable : voir README.md"; exit 1
fi
exec .venv/bin/python -m customlab.gui
