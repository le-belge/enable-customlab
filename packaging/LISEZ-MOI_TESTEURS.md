# e-NABLE CustomLab — version de test 0.9.0

Application gratuite et hors ligne pour dimensionner, personnaliser et exporter des pièces de mains/bras e-NABLE. **Expérimentale** : aucune pièce n'a été validée à l'impression ni à l'essayage ; à faire relire par un bénévole e-NABLE compétent avant tout usage.

## Installer
**Mac** (Apple Silicon : M1 et suivants) : décompressez `e-NABLE_CustomLab_mac.zip`, glissez l'appli dans Applications, puis double-cliquez dessus. macOS la bloque (« Apple n'a pas pu vérifier… ») parce qu'elle n'est pas notariée. Pour l'autoriser :
1. Cliquez sur « OK » (ou « Terminé »).
2. Ouvrez **Réglages Système → Confidentialité et sécurité**, descendez jusqu'au message sur « e-NABLE CustomLab » et cliquez sur **Ouvrir quand même** (mot de passe ou Touch ID).
3. Rouvrez l'appli et confirmez « Ouvrir ». Cela n'est à faire qu'une fois.
Sur un macOS plus ancien (avant 15), le clic droit sur l'appli → Ouvrir fonctionne aussi. Dernier recours, dans le Terminal : `xattr -dr com.apple.quarantine "/Applications/e-NABLE CustomLab.app"`.
**Windows** : décompressez `e-NABLE_CustomLab_windows.zip`, lancez `CustomLab\CustomLab.exe`. Si SmartScreen s'affiche : « Informations complémentaires » → « Exécuter quand même ».

## Premier lancement
- La **Phoenix** fonctionne tout de suite (pièces incluses).
- Une fenêtre **Fichiers sources** s'ouvre au premier lancement (menu Aide → Fichiers sources pour la rouvrir). Pour la Kinetic Hand, le Kinetic Arm ou l'Unlimbited Arm : « Ouvrir la page officielle » → téléchargez les fichiers → « Ajouter le .zip téléchargé… » et choisissez le fichier. CustomLab le range tout seul ; quand la ligne passe au ✓ vert, c'est prêt.
- Pour la gravure et l'Unlimbited Arm, installez aussi **OpenSCAD** (gratuit, openscad.org) ; il est détecté automatiquement.
- Le menu **Aide → Tuto** résume les méthodes de mise à l'échelle de chaque appareil.

## Ce que nous voulons savoir
L'appli se lance-t-elle ? Les fichiers sources sont-ils détectés ? Les mesures et échelles vous paraissent-elles cohérentes avec le manuel ? Les STL/3MF s'ouvrent-ils dans votre trancheur ? Notez le système (Mac/Windows, version) et joignez une capture en cas de problème.
Vos données restent sur votre ordinateur (dossier `.customlab` de votre dossier personnel).
