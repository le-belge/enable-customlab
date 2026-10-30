# Procédure de fabrication et validation — X1C + AMS

**Statut : aucune validation physique effectuée.** Cases à cocher par un bénévole.

1. Fournir le `.scad` officiel (Thingiverse, licence relue) ; installer OpenSCAD.
2. `python3 -m customlab size <appareil> --side … --part … --set ID=VAL --scad fichier.scad --out piece.stl` pour chaque pièce.
3. [ ] Vérifier dans Bambu Studio : import STL, dimensions de chaque pièce, orientation, supports.
4. Démo décoration : `python3 -m customlab demo-svg examples/star.svg` → `out/demo.3mf`.
   - [ ] Le 3MF s'ouvre dans Bambu Studio ? [ ] Les deux objets gardent des couleurs/filaments distincts ? [ ] Slicing OK ? (Sinon : exporter les STL séparés et assigner le filament manuellement.)
   - [ ] Idem OrcaSlicer / PrusaSlicer / Cura.
5. [ ] Impression de test du panneau démo ; relever l'épaisseur réelle et le rendu relief/gravure (profondeur 0,6 mm par défaut, à régler selon buse).
6. [ ] Assemblage à blanc, jeux et mobilité vérifiés par un bénévole e-NABLE compétent avant tout essayage.
7. Un appareil n'est jamais déclaré « sûr » par le logiciel.
Résultats d'essais : à consigner ici (date, pièce, filament, observations).
