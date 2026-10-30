# Unlimbited Arm v2.1 — ce qui est établi (2026-10-24)

Source : archive Thingiverse 1672381 « The UnLimbited Arm v2.1 – Alfie Edition » (Team UnLimbited), fournie localement par l'utilisateur (`sources/unlimbited_arm/part1|part2`, non embarquée). Licence **CC BY-NC-SA** (LICENSE.txt ; en-tête du .scad : CC BY-NC-SA 4.0) : usage non commercial, attribution, **les dérivés doivent être partagés sous la même licence**. La page NIH 3D indiquait CC BY 4.0 : discordant, écarté.

## Paramètres du SCAD v2.1 (lus dans `UnLimbited_Arm_v2.1.scad`)
| Paramètre | Sens (commentaire du SCAD) | Plage officielle |
|---|---|---|
| `part` (texte) | Forearm, Cuff, Jig, Palm, Fingers, Phalanx, Pins | — |
| `LeftRight` (texte) | Left / Right (Right = miroir X) | — |
| `HandLen` | Wrist Joint to Fingertip (mm) | 135 – 230 |
| `ForearmLen` | Wrist Joint to Elbow Crease (mm) | 120 – 315 |
| `BicepCircum` | Bicep circumference (mm) — **sans « s »** | 110 – 350 |
| `CuffLength` | longueur du cuff (défaut 65) — ne pas modifier | 65 – 90 |
| `PinHoleDia` | diamètre du trou de broche (défaut 3) — ne pas modifier | 3 – 6 |
CustomLab ne passe que `part`, `LeftRight`, `HandLen`, `ForearmLen`, `BicepCircum` ; `CuffLength` et `PinHoleDia` gardent leur défaut. Les valeurs hors plage sont **refusées**, jamais corrigées.

## Ambiguïté A/B/C : levée
Le SCAD estampille sous le cuff `str(ArmVersion, BicepCircum, ForearmLen, HandLen, "/", HandPerc, "%")` (README : « Measurement A B C »). Donc **A = BicepCircum (biceps, bras atteint), B = ForearmLen (poignet → pli du coude), C = HandLen (poignet → bout du doigt)**. La liste de *paramètres* de la page e-NABLE France est correcte ; sa liste de *mesures* (A = main, C = biceps) est inversée.

## Échelle de la main (calculée par le SCAD)
`HandPerc = round(HandLen / 135 × 100)`. Palm, Fingers, Phalanx et Pins sont mis à l'échelle uniformément par `HandPerc/100` (ce sont les pièces de la Phoenix) ; Forearm, Cuff et Jig sont paramétrés par les trois mesures. Le README précise que 135 est le minimum pour la sécurité des enfants (petites pièces) et la tolérance des petites broches.
Version v2.2 (même archive, `UnLimbited_Arm_V2.2.scad`) : non retenue — paramètres numériques (`part` 1–8, `LeftRight` 0/1), `HandLen` 120–230, `BicepCircum` 160–350, `CuffLength` automatique, pièce supplémentaire (WristJig & Palm Grip). La page e-NABLE France documente la v2.1.

## Vérifié par calcul (OpenSCAD 2021.01, 24/10/2026, HandLen 150 / ForearmLen 200 / BicepCircum 220)
Les 7 pièces se rendent : Pins, Palm, Fingers, Phalanx < 1 s ; Jig 23 s ; Cuff ≈ 4 min 20 ; Forearm ≈ 5 min 12 (opérations booléennes CGAL). Échelle de la main contrôlée par test (rapport 111 %/100 % sur les broches), main droite = miroir de la gauche. Cache des pièces générées par (hash du SCAD, paramètres).

## Dans CustomLab
Étape 2 : mesures A/B/C avec schéma, échelle de la main affichée. Étape 3 : « Générer la pièce depuis le SCAD officiel » (tâche de fond, avec cache), puis personnalisation comme pour la Phoenix ; la licence (NC-SA, auteur) est recopiée dans la fiche d'export. Si les mesures changent après la génération, l'export est bloqué jusqu'à régénération. Pas de mise à l'échelle par CustomLab : le SCAD s'en charge.

## Non vérifié
Impression, essayage, tolérances réelles des broches ; zones fonctionnelles du cuff/avant-bras (fentes de sangle, canaux) : seuls les trous visibles sont protégés automatiquement ; exactitude du texte estampillé sous le cuff après décoration (la décoration ne doit pas le recouvrir). À faire valider par un bénévole e-NABLE compétent.
