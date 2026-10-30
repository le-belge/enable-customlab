# Relais Codex → Claude — 22 octobre 2026

## Faits nouveaux vérifiés

- Dossier durable : /Users/noelmichael/Documents/Codex/Projects/enable-customlab. Aucun code modifié pendant cette intervention ; ne pas refaire l'installation ni les 31 tests déjà rapportés sans changement pertinent.
- Les deux ZIP à 100 % ont été récupérés depuis les liens gauche/droite de https://3d.nih.gov/entries/3DPX-020258 : https://drive.google.com/file/d/1HODXAGyJy0au1Y6FAYdq2Jl0JDgGoaje/view et https://drive.google.com/file/d/1HbdV5iTg79NkxtgriTy8MBGKfA7NgYcD/view.
- 16 STL et leurs textes de licence/provenance sont présents sous sources/phoenix_nih_linked_100pct_20261022/{left,right}/. Les README indiquent HandPerc=100 et LeftRight. Ce sont les archives personnalisées historiques liées par NIH, pas les maillages réparés NIH ; ne pas les confondre ni présumer la compatibilité de version du dimensionnement.
- IMPORTANT : les LICENSE.txt des DEUX archives indiquent CC BY-NC 3.0, auteur jesimon, dérivés Thingiverse 2185114/2185115 de 1674320. Ne pas reprendre automatiquement l'étiquette CC-BY du bilan antérieur. Usage local seulement dans ce travail ; aucune redistribution ni modification des licences.
- 16/16 fichiers lus, coordonnées finies, exportés par customlab.meshscale.scale_stl_python à 120 %, puis relus : nombre de triangles conservé et bornes multipliées par 1,2 à la tolérance 1e-4 mm / 1e-5 relative. Ce test technique ne valide ni le dimensionnement, ni l'impression, ni l'équivalence SCAD.
- 12/16 passent customlab.meshio.is_watertight ; les paumes et les doigts, gauche ET droite, échouent. Ce constat concerne ce contrôle strict, pas un diagnostic indépendant du défaut. Ne pas réparer automatiquement.
- Résultats détaillés et SHA-256 : /Users/noelmichael/Documents/Codex/2026-10-22/referenced-chatgpt-conversation-this-is-an/outputs/phoenix-controles.json. Exports locaux de contrôle : même dossier de travail, work/phoenix-exports/ (sources tierces dérivées, ne pas distribuer).
- Pack SYNTHÉTIQUE Bambu prêt : /Users/noelmichael/Documents/Codex/2026-10-22/referenced-chatgpt-conversation-this-is-an/outputs/bambu-synthetique/. Checklist vierge : Bambu Studio n'a PAS été testé par Codex.

## Enchaînement proposé, sans redemander chaque étape

1. Lire seulement ce relais et les licences/provenances des deux archives. Confirmer la variante Phoenix visée et l'applicabilité de sa règle de dimensionnement ; garder un blocage explicite si non démontrée.
2. Ouvrir le pack synthétique dans Bambu Studio : relever version, dimensions, deux objets/couleurs, affectation filaments et résultat de tranchage. Ne rien envoyer à une imprimante. Consigner seulement les observations réelles.
3. Examiner un original Palm et Fingers de chaque côté avec un contrôle indépendant disponible (Bambu compris) ; relever défauts/avertissements sans appliquer de réparation à l'original. Distinguer composants multiples, arêtes et orientation ; ne pas conclure à partir du seul nom de fichier.
4. Si les points précédents sont satisfaits, tester import réel dans l'interface, aperçu et export ; comparer dimensions et côté avec l'original et vérifier la chaîne de provenance. Tester une mise à l'échelle documentée seulement après confirmation de variante. Aucun besoin de vraies données de bénéficiaire.
5. Conserver les fichiers d'entrée intacts ; tout résultat d'essai dans un nouveau dossier identifié expérimental. Ne jamais mélanger pack synthétique, appareil numérique et validation physique/clinique.
6. Pour les autres appareils : Thingiverse 1672381, 4618922, 6736769 renvoie encore 403 via lecture web. Ne pas répéter ces tentatives identiques. Continuer uniquement à réception du SCAD Unlimbited ou du manuel Kinetic correspondant ; ne pas inventer unités, bornes ou équivalences de versions.
7. Sans ces sources, préparer seulement les textes et schémas de mesures déjà documentées, en signalant les ambiguïtés. Avant toute modification du code, vérifier l'état courant et le périmètre autorisé. Ne pas finaliser les zones de décoration ou coques sans géométrie et zones fonctionnelles vérifiées.

## Discipline de consommation et coordination

Une tâche bornée à la fois, Sonnet / moyen, aucun sous-agent ; pas de scan .venv/ ou tools/, pas de réinstallation ni recherche répétée des mêmes fichiers. Tests ciblés après modification ; suite complète à la fin d'un lot cohérent. Un compte rendu final bref : fichiers touchés, vérifications réelles, blocages restants. Aucun push, publication, contact humain externe, dépense ou secret. Codex ne modifie plus les fichiers pendant cette reprise de Claude.

