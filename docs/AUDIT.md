# Audit technique et documentaire — e-NABLE CustomLab (Phase 0)

Date : 2026-10-22. Méthode : lecture des pages officielles via un outil de lecture web (résumés automatiques de pages).
**Aucun fichier STL/SCAD n'a été téléchargé** (téléchargement non autorisé explicitement, et Thingiverse renvoie HTTP 403 aux accès automatisés).
Toute information ci-dessous marquée « NON VÉRIFIÉ » doit être contrôlée à la main sur la source avant usage.

## 1. Sources consultées

| Source | Résultat |
|---|---|
| free3dhands.org/downloads | Kinetic Hand → Thingiverse thing:4618922 ; Kinetic Arm → thing:6736769. Aucun fichier listé sur la page. |
| free3dhands.org/our-devices | Descriptions seules (Hand : poignet ouvre/ferme les doigts ; Arm : coude actionne les doigts, poignet orientable). Aucune méthode de mise à l'échelle, aucune liste de composants. |
| e-nable.fr … /openscad/ | Procédure OpenSCAD pour Phoenix Hand et Unlimbited Arm (voir §3). Licence non indiquée sur la page. |
| e-nable.fr … /instructions-de-fabrication/ | Table des matières seulement (Phœnix, Unlimbited, Kinetix sous « Projet Robotique », « Mettre à l'échelle »). Sous-pages non lues. |
| thingiverse.com/thing:1674320, 1672381 | **403 Forbidden** — non lues. |
| hub.e-nable.org | Non lu à ce stade. |
| Recherche web (NIH 3D, Printables) | Miroirs indiquant CC-BY pour Phoenix Hand et UnLimbited Arm v2.1, **sans confirmer** que 1672381 est la même version. NON VÉRIFIÉ. |

## 2. Licences

| Appareil | Licence connue | Restrictions | Statut |
|---|---|---|---|
| Kinetic Hand | CC BY-NC-SA 4.0 (page Free3DHands) | « trial and evaluation purposes only » ; non commercial ; partage dans les mêmes conditions | Confirmée sur la page officielle |
| Kinetic Arm | Non indiquée sur la page ; probablement identique | À confirmer sur thing:6736769 | NON VÉRIFIÉ |
| Phoenix Hand | CC-BY d'après un miroir (NIH 3D) | Attribution Team UnLimbited | NON VÉRIFIÉ sur Thingiverse |
| Unlimbited Arm | CC-BY d'après un miroir (NIH 3D, v2.1) | Attribution Team UnLimbited | NON VÉRIFIÉ |

Conséquence : **ne redistribuer aucun fichier source** dans le logiciel. L'application doit demander à l'utilisateur de fournir lui-même les SCAD/STL (import local), et afficher crédits et licence de chaque profil.
Le CC BY-NC-SA des Kinetic impose que tout dérivé distribué soit non commercial et sous la même licence : à traiter dans la licence du logiciel (le code de CustomLab peut rester séparé tant qu'il ne contient pas les modèles).

## 3. Méthodes de dimensionnement documentées

**Phoenix Hand** (source : e-NABLE France, OpenSCAD) — documenté : échelle unique en pourcentage, **100 à 160**, côté gauche/droit, choix de la pièce (Palm, Box, TPins, Fingers, Phalanx, Pins, Gauntlet, Jig). Aucune formule reliant mesures du bénéficiaire et pourcentage n'est donnée sur la page lue (la page « Mettre à l'échelle » n'a pas été lue). → le moteur accepte le pourcentage ; **la conversion mesure → % reste à documenter**.

**Unlimbited Arm** — paramètres documentés : `Part` (Forearm, Cuff, Jig, Palm, Fingers, Phalanx, Pins), `LeftRight`, `HandLen`, `ForearmLen`, `BicepsCircum`, `CuffLength` et `PinHoleDia` (à ne pas modifier). Mesures : A longueur de la main valide, B longueur de l'avant-bras valide, C circonférence du biceps du côté atteint.
**Incohérence source** : la liste des mesures associe A=main, C=biceps, mais la liste des paramètres associe HandLen à « mesure C » et BicepsCircum à « mesure A ». Les profils utilisent donc les **noms de paramètres** comme identifiants et marquent `label_mapping_confirmed: false` ; l'assistant visuel ne doit pas être finalisé avant clarification (consulter le SCAD original ou e-NABLE France).
Plages de validité des mesures : **non documentées** → aucune borne inventée ; seules les valeurs ≤ 0 sont rejetées et un avertissement signale l'absence de plage validée.

**Kinetic Hand / Kinetic Arm** — aucune méthode de dimensionnement trouvée. Source possible : documentation PDF/Thingiverse (inaccessible). Free3DHands indique un contact (info@free3dhands.org) — **non contacté**, conformément aux consignes. Les modèles sont a priori des STL fixes → architecture « maillage » (sans mise à l'échelle uniforme présumée valide).

## 4. Matrice de compatibilité

| Fonction | Phoenix Hand | Unlimbited Arm | Kinetic Hand | Kinetic Arm |
|---|---|---|---|---|
| Source paramétrique (SCAD) | Oui (à fournir localement) | Oui (à fournir localement) | Non connue | Non connue |
| Moteur de dimensionnement | Expérimental (échelle %) | Expérimental (3 mesures, mapping non confirmé) | Indisponible | Indisponible |
| Génération via OpenSCAD | Code prêt, **non testé** (OpenSCAD absent, SCAD non obtenu) | idem | — | — |
| Décoration SVG | Démonstrateur sur surface générique | idem | Indisponible (zones non définies) | Indisponible |
| Coques | Non commencé | Non commencé | Non commencé | Non commencé |
| Export STL | Oui (générique) | Oui | Oui | Oui |
| Export 3MF | Écrit, **non validé dans Bambu Studio** | idem | idem | idem |

## 5. Blocages

1. Thingiverse inaccessible automatiquement → obtenir les SCAD/STL manuellement (action utilisateur) ou autoriser un téléchargement explicite.
2. OpenSCAD non installé sur la machine de développement (Bambu Studio est présent). Installation = téléchargement à autoriser.
3. PySide6 non installé ; Python système 3.9 (PySide6 et trimesh à installer dans un venv sur autorisation).
4. Ambiguïté A/C de l'Unlimbited Arm.
5. Pas de méthode Kinetic ; pas de lecture des pages « Mettre à l'échelle » et hub.e-nable.org.
6. Zones interdites/autorisées de décoration : exigent la géométrie réelle des pièces.
7. Aucune validation physique effectuée.


---
**Mise à jour 2026-10-24** : l'ambiguïté A/C est levée par le SCAD officiel v2.1 (voir `docs/POINT_20261024.md` et `docs/UNLIMBITED_ARM.md`) : A = biceps, B = avant-bras, C = main ; le paramètre s'appelle `BicepCircum` (sans « s »). Les licences des fichiers d'origine (CC BY-NC / CC BY-NC-SA) remplacent celles notées d'après les miroirs NIH.
