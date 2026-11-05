# Zones de référence

Un fichier par pièce officielle, par vue (axe) et par miroir : `<empreinte du STL>_<axe>[_m].json`, créé par le bouton
« Enregistrer comme zones de référence (pour tous) » de l'étape de personnalisation (mode Avancé).
Contenu : `{"part", "axis", "mirror", "zones": [{"kind": "forbidden" | "advised", "rect": [u0, v0, u1, v1]}]}` (mm, plan de la vue).
L'empreinte (SHA-256 du fichier STL) fait que les zones ne s'appliquent qu'au fichier exact sur lequel elles ont été tracées.
Les zones tracées par un utilisateur sur son poste (dossier `~/.customlab/zones`) remplacent celles-ci pour lui.
