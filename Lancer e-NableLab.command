#!/bin/bash
# Double-cliquez pour lancer e-NableLab (macOS). Aucune ligne de commande nécessaire.
cd "$(dirname "$0")" || exit 1
if [ ! -x ".venv/bin/python" ]; then
  osascript -e 'display alert "e-NableLab" message "Environnement Python introuvable (.venv). Voir README.md pour l'"'"'installation." as critical' 2>/dev/null
  echo "Environnement .venv introuvable : voir README.md"; exit 1
fi
exec .venv/bin/python -m customlab.gui
