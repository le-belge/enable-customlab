# Passation e-NABLE CustomLab (3 novembre 2026)

Point d'entrée pour reprendre le travail avec un nouveau compte Claude (compte e-NABLE). À lire avant tout autre fichier, puis `docs/AUDIT.md`, `docs/BILAN_SPRINT2.md`, `docs/ROADMAP.md`, `docs/TUTO_ECHELLES.md`.

## État du dépôt
- Dépôt public : https://github.com/le-belge/enable-customlab, branche `main`, dernier commit `abdbd29`.
- Pré-version publiée : **v1.0.0-beta.1** (page Releases) : `e-NABLE_CustomLab_Setup.exe` et zip Windows, zip Mac. Un tag `v*` lance `.github/workflows/build.yml`, qui construit Mac et Windows puis publie la pré-version.
- Code sous **GPL-3.0** (`LICENSE` : le code seul). Gardent leur licence propre : `customlab/bundled_parts/` (pièces Phoenix de jesimon, CC BY-NC 3.0) et le logo e-NABLE France (`customlab/assets/`, voir `LOGO_NOTICE.txt`).
- L'historique a été réécrit une fois (envoi forcé le 3 novembre) avant la mise en public. Ne pas rajouter `CLAUDE.md` au dépôt : il est volontairement ignoré (`.gitignore`) et reste en local.

## Accès à GitHub
- Sur le Mac de Michael, `git` et `gh` sont connectés au compte GitHub `le-belge` (jeton dans le trousseau, droits `repo` et `workflow`). Changer de compte Claude ne change pas cet accès.
- Sur claude.ai / sessions cloud : connecter le connecteur GitHub dans le nouveau compte et installer l'app Claude sur `le-belge`, dépôt `enable-customlab`.
- Le fichier local `.claude/settings.local.json` autorise `git add`, `git commit` et `git push origin main`. Le système refuse parfois d'auto-accorder d'autres droits (tag, visibilité, workflow) : Michael lance alors la commande lui-même.
- Aucun push, tag, release, changement de visibilité, contact externe, dépense ou secret sans accord explicite de Michael.

## Fichiers locaux, hors dépôt
`CLAUDE.md` (consignes), `sources/` (SCAD et STL officiels), `tools/` (OpenSCAD), `.venv/`, `dist/`, `build/`, `outputs/`, `experiments/`, `user_assets/`. Ne pas les scanner. Pour lancer : `.venv/bin/python -m customlab.gui` ; tests : `.venv/bin/python -m unittest discover -s tests -t .` (217 tests OK sur `main`).

## Fonctions livrées
Mode Simple/Avancé ; mesure du poignet sur photo (référence + zoom) ; guides de mise à l'échelle pas à pas par appareil ; export « tout, prêt pour Bambu » (3MF avec filaments) ; texte, SVG, image et **plusieurs motifs** ; choix de police avec aperçu ; grille des pièces ; logo e-NABLE France cliquable (e-nable.fr) et mention « par e-NABLE France » ; installateur Windows (Inno Setup, `packaging/installer.iss`).

## Travail parallèle : branche `beta2` (poussée sur GitHub, non fusionnée)
`origin/beta2` (commit `e98126b`) : 14 commits au-dessus de `v1.0.0-beta.1`, **268 tests OK** en Python 3.9 sur macOS avec OpenSCAD (39 sautés dans un environnement sans OpenSCAD ni fichiers officiels). `main` n'a pas été modifiée par cette branche. Pour la reprendre :
```
git fetch origin beta2
git checkout beta2
```
Ne pas repousser un exemplaire local plus ancien de `beta2` (les identifiants de commit ont été réécrits pour retirer des données de test personnelles).
Contenu : taille forcée annulée quand une mesure change (la valeur exportée suit l'échelle affichée) ; export multicolore : couleur 1 à la bonne échelle ; Kinetic Arm : plages par groupe (inférieurs 50-100 %, supérieurs 47,5-120 %) ; Phoenix : seules les 8 pièces du côté choisi sont listées et exportées ; vérification de l'étanchéité des STL, avec message et Gravure grisée ; recherche souple du `.scad` Unlimbited et archive en deux parties ; UTF-8 explicite pour OpenSCAD (Windows) ; journal d'erreurs (`errlog.py`) ; auto-test `--selftest` de l'exécutable ; CI renforcée (tests Ubuntu + Windows, auto-test des builds).
**À faire** : lire le résultat du workflow lancé sur `beta2` (onglet Actions), relire les différences avec `main` (`git diff main...beta2`), puis fusionner dans `main` seulement sur décision de Michael, et publier une `v1.0.0-beta.2` (tag `v*` = publication automatique d'une pré-version).

### CI de `beta2` : premier run (41710497779, 3 novembre) = ÉCHEC, côté tests uniquement
Les tests tournent sur Ubuntu et Windows avant la construction ; comme `build` dépend de `tests`, **aucune application n'a été construite** (la Release `v1.0.0-beta.1` et `main` ne sont pas touchées). En local (macOS, Python 3.9, OpenSCAD présent) les 268 tests passent. Les échecs viennent de l'environnement de test, pas d'un défaut avéré de l'application :
- **Ubuntu (Python 3.11, PySide6 récent)** : plantage de l'interpréteur (`Fatal Python error: none_dealloc`) dans `tests/test_deco.py`, `ColourSeparation.setUp`, ligne ~245 (boucle de `QImage.setPixelColor` avec `QColor`). Piste : peindre avec `QPainter.fillRect` au lieu de modifier pixel par pixel. Les tests suivants n'ont pas pu tourner : d'autres échecs sont possibles derrière. Si le même plantage touche du code de l'appli, l'auto-test `--selftest` le montrera.
- **Windows, `PermissionError [WinError 32]`** : des fichiers `.3mf` restent ouverts quand le dossier temporaire est supprimé. Dans `tests/test_core.py` (l.107), `tests/test_deco.py` (l.415) et `tests/test_gui.py` (l.186) : ouvrir les archives avec `with zipfile.ZipFile(...)`.
- **Windows, `OSError [WinError 193]`** : les faux OpenSCAD de `tests/test_utf8_paths.py` sont des scripts sans extension exécutable ; sous Windows il faut un `.bat`/`.cmd` (ou sauter ces 3 tests sur Windows, en les gardant sur Linux et macOS).
- **Windows, `test_text_is_readable_not_mirrored`** (`tests/test_deco.py`, l.69) : écart de 7080 contre 7320 pixels ; l'assertion dépend de la police disponible. À assouplir ou à fixer avec une police embarquée.
Ordre conseillé : corriger les tests sur `beta2`, relancer `gh workflow run build.yml --ref beta2`, lire le résultat, répéter. Ne fusionner dans `main` qu'une fois la CI verte et sur décision de Michael.

## Ce qui n'est PAS vérifié (ne jamais le déclarer validé)
- Aucun test sur un PC Windows ni un Mac vierge ; installateur et binaires non signés.
- Aucune impression ni essayage.
- Tableaux B1 à B3 du Kinetic Arm recopiés depuis des images : relecture humaine requise. Échelles du Kinetic Arm au-delà de 100 % et tableau des paumes pré-échelonnées : validation par un bénévole avant impression.
- Règle Phoenix (échelle = (poignet + 5) ÷ 43 × 100, plage documentée 100-160 %) non confirmée pour les STL jesimon. Hors plage : l'appli **refuse**, sans corriger.
- Accord de l'association e-NABLE France sur l'usage du logo et de la mention « par e-NABLE France » : à obtenir de son conseil d'administration.

## À faire (priorité indicative)
1. Valider `beta2` (CI et tests, voir plus haut), puis fusion et `beta.2` si Michael le décide.
2. Retours de testeurs : un père novice bloque sur l'échelle à partir de photos. Points de blocage probables : mesure sur photo sans référence ou en perspective, refus hors plage 100-160 %, double mise à l'échelle dans le slicer, installation Windows. Reproduire avec ses informations avant de modifier le code.
3. Schéma de mesure Phoenix plus clair (cote sur le pli du poignet, exemples bon / mauvais) ; schémas de mesure pour le Kinetic Hand et le Kinetic Arm.
4. Mode Simple réellement allégé (étapes 2-3), premier lancement guidé.
5. README : pointer vers la page Releases ; joindre `packaging/LISEZ-MOI_TESTEURS.md` à la release ; unifier les numéros de version.
6. Pièces Phoenix : fournir Palm et Fingers réparées (licence CC BY-NC à respecter).
7. Séance de test Windows guidée (compte accentué, chemin avec espaces, OneDrive, OpenSCAD absent puis présent, export 3MF).
8. Défauts connus : changer de langue remet les mesures à 0 ; Kinetic Arm : une seule taille forcée à la fois ; cadre léger autour de chaque motif et sélection par clic (idée).
