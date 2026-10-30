# e-NABLE CustomLab — voir docs/PARCOURS_PHOENIX.md pour le parcours complet (interface incluse)
**Lancer sans terminal** : double-cliquez sur `Lancer CustomLab.command` (macOS) ou `Lancer CustomLab.bat` (Windows).

```
# env: .venv (PySide6) + tools/OpenSCAD.app (local)
.venv/bin/python -m customlab.gui         # interface
.venv/bin/python -m customlab phoenix-scale 40
.venv/bin/python -m customlab validation-pack
python3 -m unittest discover -s tests
python3 -m customlab devices
python3 -m customlab size phoenix_hand --side left --part Palm --set scale_percent=120
python3 -m customlab demo-svg examples/star.svg --mode relief
```
Lire `docs/AUDIT.md` d'abord : les limites et blocages réels y sont listés.
