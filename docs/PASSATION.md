# Passation e-NABLE CustomLab (4 novembre 2026)

Point d'entrée pour reprendre le travail avec un nouveau compte Claude (compte e-NABLE). À lire avant tout autre fichier, puis `docs/AUDIT.md`, `docs/BILAN_SPRINT2.md`, `docs/ROADMAP.md`, `docs/TUTO_ECHELLES.md`.

## État du dépôt
- Dépôt public : https://github.com/le-belge/enable-customlab, branche `main`.
- Pré-versions publiées : **v1.0.0-beta.2** (dernière), **v1.0.0-beta.1** (page Releases) : `e-NABLE_CustomLab_Setup.exe` et zip Windows, zip Mac. Un tag `v*` lance `.github/workflows/build.yml`, qui construit Mac et Windows puis publie la pré-version.
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

## Version `v1.0.0-beta.2` (4 novembre 2026) : `beta2` fusionnée dans `main`
Contenu repris de `beta2` : taille forcée annulée quand une mesure change (la valeur exportée suit l'échelle affichée) ; export multicolore : couleur 1 à la bonne échelle ; Kinetic Arm : plages par groupe (inférieurs 50-100 %, supérieurs 47,5-120 %) ; Phoenix : seules les 8 pièces du côté choisi sont listées et exportées ; vérification de l'étanchéité des STL, avec message et Gravure grisée ; recherche souple du `.scad` Unlimbited et archive en deux parties (prolonge `unpack_nested`) ; UTF-8 explicite pour OpenSCAD (Windows) ; journal d'erreurs (`errlog.py`) ; auto-test `--selftest` ; CI : tests Ubuntu + Windows à chaque push, auto-test des applis construites.

Corrections faites pour rendre la CI verte (session cloud du 3-4 novembre) :
- **PySide6 6.12.0 exclu** : avec Python 3.9 à 3.11, chaque appel Qt sans valeur de retour retire une référence à `None`, puis `Fatal Python error: none_dealloc`. La CI est fixée à **6.11.3**, la doc de construction à `<6.12`, et `tests/test_pyside_refcount.py` échoue si une version fautive revient. **La `v1.0.0-beta.1` publiée a été construite avec 6.12.0 + Python 3.11** : elle peut planter en cours d'utilisation (non vérifié sur les binaires).
- **Windows sans fenêtre** (tests, ligne de commande, `--selftest`) : Qt offscreen ne voyait pas `C:\Windows\Fonts` et dessinait le texte en carrés vides. `customlab.windows_offscreen_fonts()` (appelé à l'import et par `deco._ensure_qt()`) règle `QT_QPA_FONTDIR`.
- Tests : archives 3MF lues en mémoire (fichier verrouillé sous Windows), faux OpenSCAD lancé via `python`, test du « L » coupé au milieu du cadre de la lettre.
- Résultat : **271 tests OK, 39 sautés** (Ubuntu et Windows en CI ; Python 3.9, 3.11, 3.13 en local) ; construction manuelle (run 41717234381) : Mac et Windows construits, `--selftest` OK sur les deux.

## Ce qui n'est PAS vérifié (ne jamais le déclarer validé)
- Aucun test sur un PC Windows ni un Mac vierge ; installateur et binaires non signés.
- Aucune impression ni essayage.
- Tableaux B1 à B3 du Kinetic Arm recopiés depuis des images : relecture humaine requise. Échelles du Kinetic Arm au-delà de 100 % et tableau des paumes pré-échelonnées : validation par un bénévole avant impression.
- Règle Phoenix (échelle = (poignet + 5) ÷ 43 × 100, plage documentée 100-160 %) non confirmée pour les STL jesimon. Hors plage : l'appli **refuse**, sans corriger.
- Accord de l'association e-NABLE France sur l'usage du logo et de la mention « par e-NABLE France » : à obtenir de son conseil d'administration.

## À faire (priorité indicative)
1. Faire essayer la `v1.0.0-beta.2` sur un vrai PC Windows et un vrai Mac (appli avec fenêtre, gravure avec OpenSCAD, export 3MF) ; prévenir les testeurs de la beta.1 de passer à la beta.2.
2. Retours de testeurs : un père novice bloque sur l'échelle à partir de photos. Points de blocage probables : mesure sur photo sans référence ou en perspective, refus hors plage 100-160 %, double mise à l'échelle dans le slicer, installation Windows. Reproduire avec ses informations avant de modifier le code.
3. Schéma de mesure Phoenix plus clair (cote sur le pli du poignet, exemples bon / mauvais) ; schémas de mesure pour le Kinetic Hand et le Kinetic Arm.
4. Mode Simple réellement allégé (étapes 2-3), premier lancement guidé.
5. README : pointer vers la page Releases ; joindre `packaging/LISEZ-MOI_TESTEURS.md` à la release ; unifier les numéros de version.
6. Pièces Phoenix : fournir Palm et Fingers réparées (licence CC BY-NC à respecter).
7. Séance de test Windows guidée (compte accentué, chemin avec espaces, OneDrive, OpenSCAD absent puis présent, export 3MF).
8. Défauts connus : changer de langue remet les mesures à 0 ; Kinetic Arm : une seule taille forcée à la fois ; cadre léger autour de chaque motif et sélection par clic (idée).
