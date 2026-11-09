# Multicolore et multimatière (EXPÉRIMENTAL, phase 1)

Export « toutes les pièces » : chaque pièce reçoit une **matière** (PLA, PETG, ASA, TPU 95A, TPU 85A) et une **couleur**. e-NableLab
crée en plus `APPAREIL_Bambu_pret.3mf` : toutes les pièces sur le plateau, chacune avec son filament, et le motif de la pièce
personnalisée avec ses couleurs (même matière que la pièce). Si tout ne tient pas sur un plateau : `…_plateau1.3mf`, `…_plateau2.3mf`.
Le mode d'emploi `APPAREIL_LISEZ-MOI_Bambu.txt` liste les filaments dans l'ordre, avec les pièces qui les utilisent.

- **Matière proposée** : TPU 95A si le nom du fichier contient « TPU », « flex » ou « souple », sinon PLA. Ce n'est qu'une
  suggestion : vérifier dans le manuel de l'appareil (ex. Kinetic Hand : charnières et couvercle de paume en TPU).
- **Imprimante** (mémorisée) : X1C/P1S + 1 AMS = 5 filaments au plus, dont 1 seul souple (le TPU ne passe pas par l'AMS, bobine
  externe) ; « Autre » = pas de contrôle.
  Trop de filaments ou de bobines souples : le 3MF de l'appareil n'est **pas** créé (refus, sans rien modifier) ; les pièces restent exportées.
- **Matière dans le 3MF** : `filament_type` est ajouté à `Metadata/project_settings.config`. **Non vérifié dans Bambu Studio**
  (seules les couleurs l'ont été, voir `BAMBU_FILAMENTS.md`) : si la matière n'est pas reprise, choisir les préréglages à la main.
- Mode Simple : matières proposées et dernière imprimante choisie, sans tableau. Mode Avancé : tableau Pièce / Matière / Couleur.

Non fait : zones souples dans une même pièce (ex. bouts de doigts en TPU sur une paume en PLA), placement avec rotation,
plusieurs plateaux dans un seul 3MF. **Aucune impression ni essayage** : souplesse, tenue et adhérence entre matières non vérifiées.

## Ouvrir un 3MF, choix de l'export
- Étape de personnalisation : « Ou ouvrir un autre fichier (STL ou 3MF)… ». Un 3MF est converti en STL dans `~/.customlab/imported`
  (l'original n'est pas modifié) ; s'il contient plusieurs objets, l'appli demande lequel personnaliser (ou tous, fusionnés).
  Les noms des objets sont lus comme Bambu Studio les enregistre ; couleurs et matières du 3MF ne sont pas reprises.
  README.txt + LICENSE.txt trouvés à côté du 3MF sont recopiés pour que la licence reste reconnue.
  Testé sur les 3MF écrits par e-NableLab ; un 3MF enregistré par Bambu Studio lui-même n'a pas encore été essayé.
- Mode Simple : deux boutons d'export, « Exporter tout, prêt pour Bambu… » et « Exporter seulement la pièce en cours… ».
