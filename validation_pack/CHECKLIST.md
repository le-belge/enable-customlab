# Bambu Studio import validation (SYNTHETIC files, not an e-NABLE device)
Fill in by hand. Nothing here is validated until you tick it.

- [ ] synthetic_panel.stl imports; size ~60 x 70 mm (curved, 2.5 mm thick)
- [ ] synthetic_two_colours.3mf imports as 2 objects / 2 filament colours (grey, red)
- [ ] AMS filament mapping works; slicing succeeds; preview shows both colours
- [ ] Same checks in OrcaSlicer / PrusaSlicer / Cura (3MF colours may not map: note it)
Observations / Bambu Studio version:

## Observations réelles — Bambu Studio 02.08.03.66, ligne de commande, 2026-10-22 (pas l'interface graphique)
- [x] STL/3MF synthétiques importés, 2 objets, géométrie intacte ; tranchage OK.
- [ ] 3MF : couleurs NON reprises (« no filament colors found ») → multicolore non validé ; test graphique avec profil X1C + AMS requis.
- [ ] Autres slicers : non testés.
