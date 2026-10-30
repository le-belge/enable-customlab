# Résultats du 2026-10-22 (reprise Claude, suite au relais Codex)

Aucun code modifié. Contrôles réalisés avec Bambu Studio 02.08.03.66 **en ligne de commande** (`--datadir` isolé dans le dossier temporaire, aucun envoi à une imprimante) : ce n'est **pas** un test de l'interface graphique ni de l'AMS.

## 1. Variante Phoenix des archives liées par NIH
- Origine : Thingiverse 2185114 (gauche) / 2185115 (droite), « Phoenix Hand 100 % Scale » par jesimon, **CC BY-NC 3.0**, dérivés de thing:1674320 générés par le Customizer (fichiers datés 2017-03-17). Paramètres utilisés : `HandPerc=100`, `LeftRight`.
- Écart de version : la page e-NABLE France documente un paramètre `scale` (100–160) ; ces archives utilisent `HandPerc`. **Rien ne démontre** que la référence « 43 mm » de la formule e-NABLE France correspond à cette version. → **Blocage explicite** : la mise à l'échelle documentée n'est pas validée pour ces fichiers. Usage local uniquement ; ne pas redistribuer. Le profil `phoenix_hand` (licence « CC-BY ») est à corriger en conséquence (non fait : code/profils non touchés).

## 2. Pack synthétique dans Bambu Studio (CLI)
- Import réussi : 2 objets (« panel », « decoration »), géométrie intacte (volume panneau 10203,1 mm³ = valeur calculée par CustomLab), 0 arête ouverte, 0 arête non-manifold, tranchage OK.
- Avertissement : « no filament colors found in projects » → **les couleurs du 3MF (basematerials) ne sont pas reprises** ; tranchage mono-filament (#00AE42). Avertissement non critique « decoration has floating regions » (relief tranché isolément).
- Bambu stocke l'affectation filament par objet dans `Metadata/model_settings.config` (`extruder`) et les couleurs dans `project_settings.config`. Deux essais d'ajout minimal de ces métadonnées n'ont **rien changé** ; même un 3MF produit par Bambu avec deux filaments reste mono-filament en CLI (profil par défaut sans AMS). **Le 3MF multicolore n'est donc ni validé ni réfuté** : il faut une session graphique avec le profil X1C + AMS. Tant que ce n'est pas fait, exporter les STL séparés et affecter les filaments à la main.

## 3. Originaux Palm et Fingers (gauche et droite)
| Fichier | Contrôle strict CustomLab | Bambu (CLI) |
|---|---|---|
| Palm G/D | non étanche | 3 composants, 9 arêtes non-manifold, faces inversées signalées, 0 arête ouverte |
| Fingers G/D | non étanche | 5 composants, 2 arêtes non-manifold, faces inversées signalées, 0 arête ouverte |
| Pins G/D (témoin) | étanche | 13 composants, aucun défaut |
Tranchage réussi dans tous les cas, sans réparation appliquée ; originaux inchangés (SHA-256 identiques avant/après). Conclusion : l'échec du contrôle strict vient d'arêtes partagées par plus de deux faces et d'orientations incohérentes, pas de trous. Impact à l'impression non évalué.

## 4. Aller-retour réel par l'interface (100 % seulement)
Dossier : `experiments/gui_roundtrip_100pct_EXPERIMENTAL_20261022/` (dérivés de sources CC BY-NC : ne pas distribuer). Import → aperçu → export pour les 4 pièces : nombre de triangles conservé, écart max des sommets ≤ 8e-6 mm (arrondi float32), volumes identiques à 2e-6 près. Les pièces droites sont l'**image miroir exacte en X** des gauches (écart 0,0 mm). Poignet 38 mm = 100 % exactement (identité). Ce test ne valide pas le dimensionnement, l'impression ni l'équivalence SCAD.

## 5. Prochain vrai blocage
1. Test **graphique** Bambu Studio (profil X1C + AMS) du 3MF multicolore : action sur votre machine ou accès écran à autoriser.
2. Confirmer la variante Phoenix (SCAD 1674320 / valeur de référence) avant toute mise à l'échelle documentée.
3. SCAD Unlimbited / manuel Kinetic toujours absents (Thingiverse 403, non retenté).
