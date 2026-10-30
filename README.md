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

## Installer l'application (versions de test)

Les versions de test se téléchargent depuis l'onglet **Actions** du dépôt (workflow « Build test apps », section *Artifacts* du dernier run réussi).

**Windows** : télécharger `e-NABLE_CustomLab_windows`, décompresser, lancer `e-NABLE_CustomLab_Setup.exe` (sans droits administrateur). L'application n'est pas signée : Windows affiche « Windows a protégé votre ordinateur » → *Informations complémentaires* → *Exécuter quand même*.
Installer aussi [OpenSCAD](https://openscad.org) (gravure et bras Unlimbited), puis ajouter vos sources via *Fichier → Fichiers sources*.

**macOS** : télécharger `e-NABLE_CustomLab_mac`, décompresser, ouvrir `e-NABLE CustomLab.app` (clic droit → *Ouvrir* la première fois).

Ces versions n'ont pas été testées sur un poste vierge. Les fichiers sources (SCAD / STL officiels) ne sont pas fournis.

## Licence

Le **code de CustomLab** est publié sous **GNU GPL v3** (fichier `LICENSE`).

La licence ne couvre **que le code**. Ces éléments gardent leur propre licence :
- `customlab/bundled_parts/` : pièces Phoenix de jesimon, **CC BY-NC 3.0** (usage non commercial, attribution ; voir `customlab/bundled_parts/NOTICE.txt`).
- `customlab/assets/enable_france_logo.png` : logo e-NABLE France, droits réservés à leur titulaire (voir `customlab/assets/LOGO_NOTICE.txt`).
- Les SCAD et STL officiels (Team UnLimbited, Mat Bowtell / Free 3D Hands…) ne sont pas fournis : l'utilisateur les ajoute lui-même et leurs licences s'appliquent.

Logiciel EXPÉRIMENTAL : aucune validation médicale ni d'impression. Voir `docs/AUDIT.md`.
