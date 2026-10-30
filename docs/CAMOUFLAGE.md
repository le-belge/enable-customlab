# Camouflage (expérimental)

Motif organique à 3 couleurs généré par CustomLab (aucune image tierce), appliqué à toute la surface décorable d'une pièce.

- **Styles** : `fr` (style Centre Europe : vert olive #5B6236, brun #6B4A2E, noir #1E1E1C ; pièce conseillée : sable #C2B280) et `winter`
  (gris clair #C5CBD0, gris acier #8D969E, anthracite #4B5259 ; pièce conseillée : blanc #F2F4F5). Ce sont des **styles inspirés**, pas la
  reproduction d'un motif officiel. La couleur de la pièce elle-même est le filament 1 ; les 3 teintes sont les filaments 2 à 4.
- **Réglages** : variante (graine), taille des taches (10–120 mm, défaut 28), profondeur (défaut 0,6 mm, incrustation affleurante),
  qualité (défaut Standard 0,25 mm : le fin multiplie par 3 le nombre de triangles).
- **Où le camouflage s'arrête** : zones protégées automatiquement (trous, fentes, bords raides), zones interdites tracées, pentes > 35°,
  1 mm autour de tout bord ; les filaments plus fins que 0,8 mm sont supprimés. Gravure refusée.
- **Plusieurs pièces** : bouton « Appliquer le camouflage à plusieurs pièces… » → une variante, une vue, les zones tracées et l'échelle
  d'export propres à chaque pièce ; un dossier par pièce (3MF Bambu prêt, STL séparés, fiche, attribution) + `RECAP_camouflage.txt/json`.
  Une pièce sans surface décorable ou dont l'échelle sort de la plage documentée est ignorée et signalée, jamais corrigée.
- **Limites** : les motifs ne se raccordent pas d'une pièce à l'autre (positions d'assemblage inconnues) ; zones fonctionnelles non
  détectées ; aucune impression ni validation physique ; le multicolore fin augmente le temps d'impression et le déchet de purge.
