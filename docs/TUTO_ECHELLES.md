# Tuto rapide : mesurer, mettre à l'échelle, personnaliser, exporter

Résumé des méthodes **documentées** pour chaque appareil, à lire avant de se lancer. Tout est EXPÉRIMENTAL : aucun essayage ni impression n'a été fait avec CustomLab. Une valeur hors plage est **refusée**, jamais corrigée. Imprimer d'abord une pièce d'essai (paume ou gabarit) avant de fabriquer l'appareil.

## L'ordre à suivre
1. **Choisir l'appareil** (page d'accueil).
2. **Mesurer** le bénéficiaire (étape 2) : voir la méthode de chaque appareil ci-dessous.
3. **Personnaliser** (étape 3) : on place le motif sur la pièce **à la taille standard (100 %)**. Le motif suit ensuite l'échelle à l'export.
4. **Résultat / export** (étape 4) : cocher l'application de l'échelle, vérifier le récapitulatif (échelle, pièces, filaments), puis exporter la pièce ou **toutes les pièces à cette échelle**.
5. **Ouvrir le 3MF dans Bambu Studio** pour les pièces multicolores.

## Phoenix Unlimbited Hand
- **Mesure** : largeur du poignet de la main atteinte, en mm, sans ajouter de marge.
- **Calcul** : échelle % = (poignet + 5 mm) ÷ 43 × 100 (source e-NABLE France, « Mettre à l'échelle »).
- **Plage documentée** : 100 à 160 % (soit un poignet d'environ 38 à 64 mm avec la marge de 5 mm). Hors plage : refusé.
- **Échelle uniforme** pour toutes les pièces.
- **Réserve** : la règle est confirmée pour le SCAD Team UnLimbited 1674320. Pour les STL embarqués (jesimon, paramètre `HandPerc`), le lien avec la référence de 43 mm n'est **pas confirmé** : vérifier avec la paume d'essai ou le gabarit Phoenix.
- On peut aussi saisir **directement un pourcentage**.

## Kinetic Hand
- **Mesures** : largeur du poignet et longueur de la paume de la main atteinte (facultatif : largeur maximale de la paume, longueur de la main saine).
- **Calcul** (manuel Kinetic Hand, annexe 1) : largeur du poignet + 3 mm → ligne la plus proche du « Hand Scaling Chart » (50 à 100 %, pas de 2,5 %, égalité → échelle supérieure).
- **Échelle uniforme** pour toutes les pièces. L'échelle par axe est calculée à titre d'information seulement et jamais appliquée.
- **Insert souple A–E** : espace libre dans la paume = longueur de paume du modèle − longueur mesurée → insert le plus proche.
- **Limites** : plage 50–100 %, minimum **55 %** recommandé par le guide d'impression.
- **Main gauche** : toutes les pièces sont des mains droites ; la main gauche est la symétrie en X, appliquée **avant** la décoration.
- Exemples du manuel reproduits : poignet 48 → 72,5 % + insert D.

## Kinetic Arm
Méthode des pages 28–33 du manuel (tableaux B1–B4) :
1. Longueur de la main saine → échelle des composants **inférieurs** (arrondie vers le bas ; 50–100 %).
2. Largeur du coude du membre résiduel → type d'avant-bras A–F (arrondi vers le haut).
3. (échelle inférieure, type) → échelle des composants **supérieurs**.
4. Longueur du membre résiduel → insert A–Q (arrondi vers le haut).
5. (insert, type) → languette 1–4 et doublure néoprène 1–12.
- **Fichiers pré-échelonnés** (Palm, mécanisme de verrouillage, tendeurs) : on prend le bon fichier, **jamais mis à l'échelle** dans le trancheur. CustomLab avertit si le fichier ne correspond pas à l'échelle calculée.
- Contrôle documenté : membre résiduel = 15 à 70 % de l'avant-bras valide.
- **À relire** : les tableaux B1–B3 ont été recopiés depuis des images ; un bénévole doit en vérifier quelques lignes. La règle de symétrie du bras gauche (fichiers « RH ») est à confirmer.
- Le manuel demande un bras d'essai et une relecture par un professionnel de santé en cas de changement d'échelle.

## Unlimbited Arm v2.1
Pas de mise à l'échelle par CustomLab : le **SCAD officiel** calcule les pièces à partir de trois mesures (noms des paramètres, pas les lettres A/B/C de la page e-NABLE France, qui se contredisent) :

| Mesure | Paramètre | Plage officielle |
|---|---|---|
| Longueur de la main saine (poignet → bout du doigt) | `HandLen` | 135 – 230 mm |
| Longueur de l'avant-bras (poignet → pli du coude) | `ForearmLen` | 120 – 315 mm |
| Circonférence du biceps, bras atteint | `BicepCircum` | 110 – 350 mm |

- Échelle de la main : `HandPerc = round(HandLen ÷ 135 × 100)`. Palm, Fingers, Phalanx et Pins suivent cette échelle ; Forearm, Cuff et Jig sont paramétrés par les trois mesures.
- 135 mm est le minimum pour la sécurité des enfants (petites pièces, tolérance des broches).
- Il faut **générer** chaque pièce (de 1 s pour les petites à 5 min pour l'avant-bras). Si les mesures changent, régénérer avant d'exporter.
- Licence CC BY-NC-SA : les dérivés doivent être partagés sous la même licence.

## Personnaliser sans se tromper
- Le motif se place sur le modèle à **100 %** ; l'échelle d'export s'applique ensuite à la pièce **et** au motif.
- Modes : relief (ajouté), gravure (retirée, pièce étanche seulement), incrustation affleurante (réglage de dépassement possible).
- Les zones fonctionnelles (articulations, trous de broches, passages de câbles, surfaces au contact de la peau) ne sont **pas toutes détectées** : seuls les trous visibles sont protégés. À marquer à la main et à faire relire.
- Détails de moins de 0,8 mm (2 × la buse de 0,4 mm) : avertissement, ils peuvent ne pas s'imprimer.
- Couleurs : jusqu'à 4 ; le **blanc** est traité comme vide (reste en filament de la base). Un fichier 3MF multicolore est prêt pour Bambu Studio (testé sur une version).

## Ce qui reste non vérifié
Impression réelle, essayage, ajustement physique des pièces, tableaux B1–B4 du Kinetic Arm relus par un humain, règle Phoenix pour les STL jesimon, Windows.
