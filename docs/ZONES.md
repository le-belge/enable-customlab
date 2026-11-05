# Zones conseillées et interdites

Étape de personnalisation, mode Avancé :
- **Tracer une zone interdite** (rouge) / **Tracer une zone conseillée** (vert) : glisser un rectangle sur la vue de placement.
- Motif dans une zone rouge : **refusé**, sauf si « **Valider malgré les zones interdites** » est cochée (visible aussi en mode Simple).
  Le refus devient alors un avertissement, et le fichier JSON de l'export garde la trace (`forbidden_zones_overridden`,
  `spec.allow_forbidden_zones`). La protection automatique (trous, fentes, bords pentus, orange) n'est pas levée par cette case :
  sa marge se règle avec « Marge auto autour des trous » (0 = désactivée).
- Zones vertes : au chargement de la pièce, le motif est centré dans la plus grande ; un avertissement indique la part du motif hors des zones vertes.
- **Enregistrer comme zones de référence (pour tous)** : écrit les zones de la pièce dans `customlab/zone_refs/` (fichier lié à
  l'empreinte exacte du STL, à la vue et au miroir). Ces fichiers sont à ajouter au dépôt (commit) pour être livrés avec l'appli.
- Chez un utilisateur, ses propres zones (dossier `~/.customlab/zones`) remplacent les zones de référence de la pièce ;
  « Effacer les zones » enregistre une liste vide (les zones de référence ne reviennent pas tant qu'il n'en retrace pas).

Les anciennes zones (rectangles simples) sont lues comme des zones interdites.
