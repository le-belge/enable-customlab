# Fabriquer les applications de test (Mac et Windows)

Version de test **1.0.0-beta.2** : expérimentale, non signée, aucune pièce validée à l'impression.

## Contenu / non-contenu
- Inclus : le code, les profils, les 16 pièces Phoenix (jesimon, CC BY-NC 3.0, avec leurs licences et la NOTICE), le tuto, le logo e-Nable France (accord de l'association à confirmer avant toute diffusion hors des bénévoles).
- **Non inclus** : les fichiers SCAD/STL des autres appareils (à télécharger sur les pages officielles : menu Aide → « Fichiers sources »), et OpenSCAD (à installer depuis openscad.org, utile pour la gravure et l'Unlimbited Arm).

## Mac (sur un Mac, depuis la racine du projet)
```
packaging/build_mac.sh
```
Résultat : `dist/e-NableLab_mac.zip` (signature ad hoc, sans compte développeur Apple, donc non notariée).

## Windows (à faire sur un PC Windows : PyInstaller ne compile pas pour Windows depuis un Mac)
1. Installer Python 3.9 ou plus récent (python.org).
2. Dans le dossier du projet :
```
py -3 -m venv .venv
.venv\Scripts\python -m pip install "PySide6-Essentials<6.12" numpy pyinstaller
packaging\build_windows.bat
```
PySide6 6.12.0 est exclu : avec Python 3.9 à 3.11, il fait planter l'appli (« Fatal Python error: none_dealloc »). La CI utilise 6.11.3.
Résultat : `dist\e-NableLab_windows.zip` (dossier `e-NableLab\` avec `e-NableLab.exe`). Non signé : Windows SmartScreen affichera « Windows a protégé votre ordinateur » → « Informations complémentaires » → « Exécuter quand même ».
**La version Windows n'a jamais été lancée** : elle est à tester par un testeur sur PC.

Auto-test sans fenêtre (imports, profils, mise à l'échelle et export d'une pièce Phoenix incluse dans un dossier temporaire), code de sortie 0 = OK, 1 = échec :
`e-NableLab.exe --selftest --report selftest.txt` (Windows, le rapport est dans le fichier) ou `"e-NableLab.app/Contents/MacOS/e-NableLab" --selftest` (macOS). La CI (`.github/workflows/build.yml`) le lance sur chaque application construite.
