# Multicolore et multimatière (EXPÉRIMENTAL, phase 1)

Export « toutes les pièces » : chaque pièce reçoit une **matière** (PLA, PETG, ASA, TPU 95A, TPU 85A) et une **couleur**. CustomLab
crée en plus `APPAREIL_Bambu_pret.3mf` : toutes les pièces sur le plateau, chacune avec son filament, et le motif de la pièce
personnalisée avec ses couleurs (même matière que la pièce). Si tout ne tient pas sur un plateau : `…_plateau1.3mf`, `…_plateau2.3mf`.
Le mode d'emploi `APPAREIL_LISEZ-MOI_Bambu.txt` liste les filaments dans l'ordre, avec les pièces qui les utilisent.

- **Matière proposée** : TPU 95A si le nom du fichier contient « TPU », « flex » ou « souple », sinon PLA. Ce n'est qu'une
  suggestion : vérifier dans le manuel de l'appareil (ex. Kinetic Hand : charnières et couvercle de paume en TPU).
- **Imprimante** (mémorisée) : X1C/P1S + 1 AMS = 5 filaments au plus, dont 1 seul souple (le TPU ne passe pas par l'AMS, bobine
  externe) ; H3C = 9 outils (caractéristiques annoncées par Bambu Lab le 3/11/2026, **non testées**) ; « Autre » = pas de contrôle.
  Trop de filaments ou de bobines souples : le 3MF de l'appareil n'est **pas** créé (refus, sans rien modifier) ; les pièces restent exportées.
- **Buse 0,2 mm** (H3C) : les filaments qui ne servent qu'au motif sont signalés « buse 0,2 mm conseillée » dans le mode d'emploi
  et dans `RECAP_export.json`. Le choix de la buse se fait dans Bambu Studio : le format de ce réglage dans le 3MF n'est pas connu.
- **Matière dans le 3MF** : `filament_type` est ajouté à `Metadata/project_settings.config`. **Non vérifié dans Bambu Studio**
  (seules les couleurs l'ont été, voir `BAMBU_FILAMENTS.md`) : si la matière n'est pas reprise, choisir les préréglages à la main.
- Mode Simple : matières proposées et dernière imprimante choisie, sans tableau. Mode Avancé : tableau Pièce / Matière / Couleur.

Non fait : zones souples dans une même pièce (ex. bouts de doigts en TPU sur une paume en PLA), placement avec rotation,
plusieurs plateaux dans un seul 3MF. **Aucune impression ni essayage** : souplesse, tenue et adhérence entre matières non vérifiées.
