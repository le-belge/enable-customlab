# Kinetic Arm — dimensionnement (28/10/2026)

**Source** : « Kinetic Arm Assembly Manual » (247 p.), entrée NIH 3D 3DPX-022894 v8, Mat Bowtell / Free 3D Hands, CC BY-NC-SA. Téléchargé à la demande de l'utilisateur via l'API du site (le lien S3 direct renvoie 403, non contourné) ; SHA-256 et provenance dans `sources/kinetic_arm/manual/PROVENANCE.txt`. Non embarqué.

## Méthode (pages 28–33, annexes B1–B4 = pages 220–223)
1. Longueur de la main (majeur → poignet) → échelle des composants inférieurs, arrondi vers le **bas** (tableau 119–237 mm, 50–100 %).
2. Largeur du coude du moignon, même ligne → type d'avant-bras A–F, arrondi vers le **haut**.
3. (échelle inférieure, type) → échelle des composants supérieurs (1 décimale).
4. Longueur du moignon, même ligne → insert A–Q, arrondi vers le **haut**.
5. (insert, type) → languette 1–4 et doublure néoprène 1–12.
Paume et mécanisme de verrouillage : fichiers pré-échelonnés à l'échelle inférieure ; tendeurs : fichier le plus proche de l'échelle supérieure ; jamais mis à l'échelle dans le trancheur. Bras gauche : symétrie de certaines pièces. Contrôle documenté : moignon = 15–70 % de l'avant-bras valide. Échelle testée 50–100 %.

## Vérifications faites
- Exemple de Jake du manuel reproduit : 70 %, type B, supérieur 70 %, insert D, languette 2, doublure 4.
- Les tableaux B1–B3 ont été **recopiés depuis les images** des pages (le PDF ne contient pas leur texte) ; contrôlés par monotonie et par linéarité en l'échelle (écart ≤ 1,6 mm ; ≤ 0,2 % pour B2). Une relecture humaine d'une ou deux lignes reste souhaitable.
- Valeurs hors tableaux : refusées, jamais corrigées. 164 tests passent (`tests/test_kinetic_arm.py`).

## Limites / points ouverts
- Écart du manuel : son exemple « 81,4 % → Tensioners 80 » ne correspond pas au fichier le plus proche (82,5 %) ; CustomLab propose le fichier le plus proche et signale l'écart.
- Les 111 STL (1,7 Go, 35 M de triangles, tailles binaires cohérentes) sont téléchargés dans `sources/kinetic_arm/stl/` (non embarqués ; README/LICENSE CC BY-NC-SA 4.0 ajoutés pour la provenance).
- Décoration et export branchés pour le bras : chaque fichier a ses règles (`kinetic_arm.part_info`) — composants inférieurs/supérieurs → échelle correspondante appliquée à l'export (case cochée) ; Palm / LockMech / Tensioners = fichiers pré-échelonnés, jamais remis à l'échelle, avec avertissement si le fichier ne correspond pas à l'échelle calculée ; bras gauche : seuls les fichiers « RH » sont symétrisés en X avant décoration (déduit de la liste du manuel p. 22 et des noms de fichiers : à confirmer par un bénévole).
- Essai réel : étoile SVG en incrustation sur `UpArmCov100` (axe +y), échelle haute 70 % appliquée, STL + JSON + 3MF Bambu exportés. Les autres pièces (paume, avant-bras de 32 Mo…) n'ont pas toutes été testées : les zones fonctionnelles (charnières, passages de tendons) ne sont pas détectées, à marquer à la main.
- Un **bras d'essai** (bras supérieur, charnières de coude, avant-bras) doit être imprimé et évalué ; un changement d'échelle doit être revu par un professionnel de santé (manuel). Aucun essayage ni impression réalisés : statut **expérimental**.
