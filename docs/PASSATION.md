# Passation e-NableLab (7 novembre 2026)

Point d'entrée pour reprendre le travail (compte Claude e-NABLE). À lire avant tout autre fichier, puis `docs/MULTIMATIERE.md`, `docs/ZONES.md`, puis `docs/AUDIT.md`, `docs/BILAN_SPRINT2.md`, `docs/ROADMAP.md`, `docs/TUTO_ECHELLES.md`.

## État du dépôt
- Dépôt public : https://github.com/le-belge/enable-customlab, branche `main`.
- Pré-versions publiées : **v1.0.0-beta.2** (dernière), **v1.0.0-beta.1** (page Releases) : `e-NableLab_Setup.exe` et zip Windows, zip Mac. Un tag `v*` lance `.github/workflows/build.yml`, qui construit Mac et Windows puis publie la pré-version.
- Code sous **GPL-3.0** (`LICENSE` : le code seul). Gardent leur licence propre : `customlab/bundled_parts/` (pièces Phoenix de jesimon, CC BY-NC 3.0) et le logo e-NABLE France (`customlab/assets/`, voir `LOGO_NOTICE.txt`).
- L'historique a été réécrit une fois (envoi forcé le 3 novembre) avant la mise en public. Ne pas rajouter `CLAUDE.md` au dépôt : il est volontairement ignoré (`.gitignore`) et reste en local.

## Accès à GitHub
- Sur le Mac de Michael, `git` et `gh` sont connectés au compte GitHub `le-belge` (jeton dans le trousseau, droits `repo` et `workflow`). Changer de compte Claude ne change pas cet accès.
- Sur claude.ai / sessions cloud : connecter le connecteur GitHub dans le nouveau compte et installer l'app Claude sur `le-belge`, dépôt `enable-customlab`.
- Le fichier local `.claude/settings.local.json` autorise `git add`, `git commit` et `git push origin main`. Le système refuse parfois d'auto-accorder d'autres droits (tag, visibilité, workflow) : Michael lance alors la commande lui-même.
- Aucun push, tag, release, changement de visibilité, contact externe, dépense ou secret sans accord explicite de Michael.

## Fichiers locaux, hors dépôt
`CLAUDE.md` (consignes), `sources/` (SCAD et STL officiels), `tools/` (OpenSCAD), `.venv/`, `dist/`, `build/`, `outputs/`, `experiments/`, `user_assets/`. Ne pas les scanner. Pour lancer : `.venv/bin/python -m customlab.gui` ; tests : `.venv/bin/python -m unittest discover -s tests -t .` (271 tests OK sur `main`, 295 sur `multimatiere`).

## Fonctions livrées
Mode Simple/Avancé ; mesure du poignet sur photo (référence + zoom) ; guides de mise à l'échelle pas à pas par appareil ; export « tout, prêt pour Bambu » (3MF avec filaments) ; texte, SVG, image et **plusieurs motifs** ; choix de police avec aperçu ; grille des pièces ; logo e-NABLE France cliquable (e-nable.fr) et mention « By e-Nable France » ; installateur Windows (Inno Setup, `packaging/installer.iss`).

## Comment travailler (consignes de Michael)
- Répondre **en français, brièvement**. Ne pas renvoyer chaque décision vers « un bénévole qui valide » ; dire simplement ce qui n'est pas testé (impression, Bambu Studio, vrai PC/Mac).
- **Deux comptes Claude sur le même Mac** : l'appli **Claude Desktop** = compte **perso** ; **Claude Code dans le Terminal** = compte **e-NABLE** (michael@e-nable.fr), pour e-NableLab. Chacun a sa propre connexion (`/status`, `/logout`, `/login` dans Claude Code).
- Une session cloud (claude.ai) **ne peut pas** lancer l'appli sur le Mac ni lire `sources/` : pour tester avec fenêtre, Bambu Studio ou les fichiers Kinetic, travailler depuis Claude Code dans le Terminal du Mac.
- Donner à Michael des blocs de commandes à copier-coller **en un seul bloc**, chemin du projet : `/Users/noelmichael/Documents/Codex/Projects/enable-customlab`.
- Chaque push : demander d'abord (« pousse ? »). Push sur `main`, tag et release : accord explicite, et souvent lancés par Michael lui-même.
- `.venv` locale : PySide6 **< 6.12** obligatoire (`.venv/bin/python -m pip install "PySide6-Essentials<6.12"` si `python -c "import PySide6; print(PySide6.__version__)"` affiche 6.12).

## Branche `multimatiere` (poussée, CI verte, NON fusionnée dans `main`)
Partie de `main` (`0212e33`, v1.0.0-beta.2). **295 tests OK, 39 sautés** (Python 3.9, 3.11 ; CI Ubuntu + Windows). Pour la reprendre : `git fetch origin && git checkout multimatiere && git pull origin multimatiere`.
- **Multicolore / multimatière** (`customlab/materials.py`, `docs/MULTIMATIERE.md`) : matière (PLA, PETG, ASA, TPU 95A/85A) et couleur par pièce dans « Exporter toutes les pièces » ; TPU proposé si le nom du fichier contient TPU/flex/souple ; imprimante mémorisée : X1C/P1S + AMS (5 filaments dont 1 souple), autre. `APPAREIL_Bambu_pret.3mf` : toutes les pièces sur le(s) plateau(x), filament par pièce, motif multicolore inclus, `filament_type` déclaré (non vérifié dans Bambu Studio) ; refus si l'imprimante ne peut pas tout prendre.
- **Zones** (`docs/ZONES.md`) : interdites (rouge) et conseillées (vert), redimensionnables par coin/bord, « Annuler la dernière zone » ; refus en zone rouge sauf case « Valider malgré les zones interdites » (tracé dans la fiche d'export) ; motif centré dans la zone verte ; **zones de référence** livrées avec l'appli (`customlab/zone_refs/`, liées à l'empreinte du STL) via « Enregistrer comme zones de référence (pour tous) » ; « Marge auto autour des trous » visible en mode Simple.
- **Face à décorer** : boutons Dessus/Dessous/Gauche/Droite/Devant/Derrière + « Retourner » (aussi en mode Simple) ; avertissement si un relief tombe sur la face posée sur le plateau.
- **Ouvrir un 3MF** comme pièce (« Ou ouvrir un autre fichier (STL ou 3MF)… ») : converti en STL dans `~/.customlab/imported`, choix de l'objet, licence recopiée ; lu en mémoire (fichier jamais verrouillé).
- Mode Simple : « Exporter tout, prêt pour Bambu… » **et** « Exporter seulement la pièce en cours… ».
- Démo faite (hors dépôt) : main Phoenix complète, logo e-NABLE France 3 couleurs (38 mm) sur le dos de la paume, 3MF X1C. Logo : usage interne tant que l'association n'a pas donné son accord.

**À vérifier sur le Mac avant de fusionner** : ouverture de `APPAREIL_Bambu_pret.3mf` dans Bambu Studio (placement, matière reprise ou non) ; ouverture d'un 3MF **enregistré par Bambu Studio** ; rendu des boutons de face (chevauchement corrigé sans pouvoir le voir sur macOS) ; TPU proposé pour les bonnes pièces Kinetic. Puis : fusion dans `main` et `v1.0.0-beta.3` sur décision de Michael.

## Version `v1.0.0-beta.2` (4 novembre 2026) : `beta2` fusionnée dans `main`
Contenu repris de `beta2` : taille forcée annulée quand une mesure change (la valeur exportée suit l'échelle affichée) ; export multicolore : couleur 1 à la bonne échelle ; Kinetic Arm : plages par groupe (inférieurs 50-100 %, supérieurs 47,5-120 %) ; Phoenix : seules les 8 pièces du côté choisi sont listées et exportées ; vérification de l'étanchéité des STL, avec message et Gravure grisée ; recherche souple du `.scad` Unlimbited et archive en deux parties (prolonge `unpack_nested`) ; UTF-8 explicite pour OpenSCAD (Windows) ; journal d'erreurs (`errlog.py`) ; auto-test `--selftest` ; CI : tests Ubuntu + Windows à chaque push, auto-test des applis construites.

Corrections faites pour rendre la CI verte (session cloud du 3-4 novembre) :
- **PySide6 6.12.0 exclu** : avec Python 3.9 à 3.11, chaque appel Qt sans valeur de retour retire une référence à `None`, puis `Fatal Python error: none_dealloc`. La CI est fixée à **6.11.3**, la doc de construction à `<6.12`, et `tests/test_pyside_refcount.py` échoue si une version fautive revient. **La `v1.0.0-beta.1` publiée a été construite avec 6.12.0 + Python 3.11** : elle peut planter en cours d'utilisation (non vérifié sur les binaires).
- **Windows sans fenêtre** (tests, ligne de commande, `--selftest`) : Qt offscreen ne voyait pas `C:\Windows\Fonts` et dessinait le texte en carrés vides. `customlab.windows_offscreen_fonts()` (appelé à l'import et par `deco._ensure_qt()`) règle `QT_QPA_FONTDIR`.
- Tests : archives 3MF lues en mémoire (fichier verrouillé sous Windows), faux OpenSCAD lancé via `python`, test du « L » coupé au milieu du cadre de la lettre.
- Résultat : **271 tests OK, 39 sautés** (Ubuntu et Windows en CI ; Python 3.9, 3.11, 3.13 en local) ; construction manuelle (run 41717234381) : Mac et Windows construits, `--selftest` OK sur les deux.

## Ce qui n'est PAS vérifié (ne jamais le déclarer validé)
- Aucun test sur un PC Windows ni un Mac vierge ; installateur et binaires non signés.
- Aucune impression ni essayage (ni PLA, ni TPU, ni multimatière).
- Bambu Studio : seules les couleurs déclarées ont été vérifiées (29/10) ; matières et plateaux multi-pièces non vérifiés.
- Tableaux B1 à B3 du Kinetic Arm recopiés depuis des images : relecture humaine requise. Échelles du Kinetic Arm au-delà de 100 % et tableau des paumes pré-échelonnées : à vérifier avant impression.
- Règle Phoenix (échelle = (poignet + 5) ÷ 43 × 100, plage documentée 100-160 %) non confirmée pour les STL jesimon. Hors plage : l'appli **refuse**, sans corriger.
- Accord de l'association e-NABLE France sur l'usage du logo et de la mention « By e-Nable France » : à obtenir de l'association.

## À faire (priorité indicative)
1. Vérifications de `multimatiere` sur le Mac (liste ci-dessus), puis fusion dans `main` et `v1.0.0-beta.3` si Michael le décide.
2. Tracer et enregistrer les **zones de référence** des pièces (Phoenix, Kinetic Hand, Kinetic Arm), puis les ajouter au dépôt.
3. **Phase 2 multimatière** : matière du motif choisie séparément (motif en TPU = pastilles / stries antidérapantes en relief), formes prêtes à l'emploi.
4. Orientation : option B (réorienter la pièce elle-même, 90°/retourner, avec « orientation d'origine ») si des 3MF/STL arrivent mal orientés ; option C (rotation libre) seulement si besoin de faces inclinées.
5. Faire essayer la `v1.0.0-beta.2` sur un vrai PC Windows et un vrai Mac ; prévenir les testeurs de la beta.1 (construite avec PySide6 6.12) de passer à la beta.2.
6. Retours de testeurs : un père novice bloque sur l'échelle à partir de photos (mesure sans référence ou en perspective, refus hors plage 100-160 %, double mise à l'échelle dans le slicer, installation Windows). Reproduire avant de modifier le code.
7. Schémas de mesure (Phoenix plus clair, Kinetic Hand, Kinetic Arm) ; mode Simple allégé, premier lancement guidé.
8. README : pointer vers la page Releases ; joindre `packaging/LISEZ-MOI_TESTEURS.md` à la release ; unifier les numéros de version.
9. Défauts connus : changer de langue remet les mesures à 0 ; Kinetic Arm : une seule taille forcée à la fois.
