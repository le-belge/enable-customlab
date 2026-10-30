# Architecture

- **Python 3 + PySide6 (GUI, à venir)**, cœur sans dépendance (stdlib) pour rester testable et distribuable (Windows/macOS, hors ligne).
- `profiles/*.json` : un profil par appareil (version, pièces, entrées documentées, licence, statut `verified|experimental|unavailable`). Aucune formule hors profil.
- `profiles.py` : moteur de dimensionnement → `-D` OpenSCAD. Refuse tout paramètre non déclaré, applique uniquement les plages *documentées*, n'écrase jamais les paramètres fixes du SCAD (ex. `PinHoleDia`), pas de mise à l'échelle uniforme implicite.
- `openscad.py` : exécution headless sur un `.scad` **fourni par l'utilisateur** (aucune source tierce embarquée : licences non vérifiées / NC-SA).
- Profils `kind: "mesh"` (Kinetic) : architecture séparée prévue (déformation par zones, jeux préservés) — non implémentée, faute de méthode documentée.
- `svgdeco.py` : projection SVG → surface courbe (relief / gravure / affleurant), volumes séparés par couleur. Démonstrateur sur panneau cylindrique générique.
- `meshio.py` : STL, contrôles (étanchéité, volume, bbox), 3MF multi-matériaux (non validé Bambu Studio).
- `store.py` : profils bénéficiaires pseudonymisés (alias, mesures, historique, comparaison).
- Visualisation 3D prévue : `pyqtgraph`/`QtQuick3D` ou VTK (à trancher à l'installation de PySide6) ; `trimesh` envisagé pour interférences/épaisseurs (MIT).
Licences : à vérifier pour chaque dépendance avant distribution (PySide6 = LGPL ; OpenSCAD = GPL, appelé comme processus externe).
