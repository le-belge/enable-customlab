# Filaments déclarés dans le 3MF

Constat (2026-10-29) : en ouvrant un `_Bambu_pret.3mf` à 3 couleurs, Bambu Studio affichait le filament 1 pour « Couleur 2 » et « Couleur 3 »
alors que le fichier écrit bien 2, 3 et 4 (`Metadata/model_settings.config`). Hypothèse : le projet n'avait pas assez de filaments.

Correction : `bambu3mf.WITH_FILAMENT_CONFIG = True` (défaut) ajoute `Metadata/project_settings.config` (JSON minimal : `filament_colour`,
`filament_diameter`) pour que Bambu crée N filaments aux couleurs du motif (base = blanc `#FFFFFF`, à remplacer par la vraie couleur).

Vérification : le fichier d'essai `TEST_filaments_Bambu.3mf` a été ouvert avec succès dans Bambu Studio par l'utilisateur (2026-10-29 ; version
de Bambu Studio non relevée ; préréglages imprimante/processus non vérifiés explicitement). Autres versions non testées. Pour revenir à l'ancien
comportement : `WITH_FILAMENT_CONFIG = False`.
