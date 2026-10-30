# Kinetic Hand — dimensionnement

**Source** : « Assembly Manual - Kinetic Hand » (annexes 1 et 2), Free 3D Hands / MatBowtell, CC BY-NC-SA 4.0 ; STL (336 Mo) lus localement, non embarqués.

## Méthode
Largeur du poignet de la main atteinte + 3 mm → ligne la plus proche du « Hand Scaling Chart » (50–100 %, pas de 2,5 %, égalité → échelle supérieure) → échelle uniforme de toutes les pièces. Espace libre dans la paume = longueur de paume du modèle − longueur mesurée → insert souple A–E le plus proche. Échelle avancée (par axe) : calculée à titre d'information, jamais appliquée. Minimum 55 % d'après le guide d'impression. Toutes les pièces sont des mains droites ; main gauche = symétrie en X **avant** décoration. Paume d'essai obligatoire.

## Vérifications
Exemples du manuel reproduits (poignet 48 → 72,5 % + insert D ; main saine 178 → Z 82,5 % + insert E). Tests : `tests/test_kinetic_hand.py`, `tests/test_kinetic_flow.py`.

## Limites
Paume « tissée » refusée à la décoration ; couvercle de gantelet décorable. Zones fonctionnelles à marquer à la main. Aucun essayage ni impression : statut expérimental.
