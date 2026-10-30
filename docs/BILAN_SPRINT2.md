# Bilan Sprint 2 (2026-10-22)

Environnement : venv `.venv` (Python 3.9, PySide6-Essentials 6.10.3, numpy), OpenSCAD 2021.01 officiel (dmg files.openscad.org, SHA-256 4e4568e1…3635e) copié dans `tools/OpenSCAD.app` (Intel, via Rosetta). Aucun autre projet touché, aucun push.
Tests : `.venv/bin/python -m unittest discover -s tests -t .` → **31 tests OK** (13 du sprint 1 conservés + 18 nouveaux : formule Phoenix, bornes, régressions Arm/Kinetic, contrôles Kinetic Arm, OpenSCAD bout en bout, GUI hors écran).

| | Phoenix Hand | Unlimbited Arm | Kinetic Hand | Kinetic Arm |
|---|---|---|---|---|
| Source étudiée | e-NABLE FR « Mettre à l'échelle » ; NIH 3D 3DPX-020258 v3 (CC-BY 4.0, STL 100 %, SCAD absent) | e-NABLE FR page OpenSCAD ; NIH 3D 3DPX-020264 v2 (CC BY 4.0, STL v2.1/2.2, aucun SCAD) | free3dhands.org (downloads, global-reach) ; NIH 3D 3DPX-022002 | NIH 3D 3DPX-022894 v8 (CC BY-NC-SA 4.0) ; thing:6736769 |
| Méthode identifiée | **Oui** : %=((poignet+marge)/43)×100, marge 5 mm, plage 100–160 % | Partielle : 3 mesures passées au SCAD ; noms de paramètres sans ambiguïté, lettres A/C contradictoires | **Non** : annexe « advanced scaling » du manuel 99 p. non lue (manuel lié à Thingiverse, 403) | Contraintes seulement : tests 50–100 % (min 50 %), moignon 15–70 % de l'avant-bras valide ; règle mesures→échelle absente |
| Paramètres confirmés | 43, 5 mm, 100–160 % | CuffLength, PinHoleDia à ne pas toucher ; unités/bornes **non** vérifiées (pas de SCAD) | — | plages ci-dessus ; pièces scalables (à 100 %) / non scalables (47,5–120 %, 50–100 %, 50–97,5 %) |
| Réellement opérationnel | Calcul guidé + refus hors plage (jamais forcé) + GUI + mise à l'échelle d'un STL 100 % fourni localement | Calcul des `-D` + rendu OpenSCAD **si .scad fourni** (non testé sur le vrai SCAD) | Rien (statut INDISPONIBLE) | Contrôle de cohérence moignon/échelle uniquement (pas un dimensionnement) |
| Tests | 7 formule/intégration + 3 GUI | 2 régression + tests moteur sprint 1 | 1 régression | 2 |
| Blocages | Équivalence « STL ×k » vs sortie SCAD non vérifiée ; STL officiels et gabarit à fournir ; Thingiverse 403 | SCAD officiel à fournir ; mapping A/C à vérifier dans le SCAD | PDF du manuel à fournir | Manuel + texte d'instructions NIH ; cohérence des versions NIH/Thingiverse à vérifier |

**Bout en bout OpenSCAD** : exécuté et testé sur un cube **synthétique** (rendu avec `-D`, mise à l'échelle `scale()+import()` identique à la mise à l'échelle Python à ±0,5 mm³). **Aucun modèle officiel n'a encore traversé la chaîne** : le téléchargement NIH passe par une page JavaScript (pas de lien direct) et Thingiverse bloque l'accès automatisé ; je n'ai rien contourné.

**Fichiers à déposer dans `sources/` (importables via la GUI)** : STL Phoenix 100 % gauche/droite (NIH 3D 3DPX-020258, CC-BY) ; gabarit Phoenix (e-NABLE FR) ; `.scad` Unlimbited Arm (thing:1672381) ; PDF du manuel Kinetic Hand (thing:4618922) ; fichiers + instructions Kinetic Arm (NIH v8 ou thing:6736769).

**Bambu Studio** : installé sur la machine. Pack synthétique prêt (`python -m customlab validation-pack`) avec `CHECKLIST.md` : **import non encore testé**, rien n'est déclaré validé.
