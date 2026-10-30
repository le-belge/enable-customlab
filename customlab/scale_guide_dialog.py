"""Help window "Mettre à l'échelle pas à pas", one guide per device: the documented method (paraphrased), screenshots of this app and a live calculator that uses the same functions as the app.

Source of the method: https://e-nable.fr/fr/fabrications/matching/mettre-a-lechelle/ (formula, 5 mm margin, 43 mm reference). The page itself gives no limits;
the 100-160 % range used by CustomLab comes from the official OpenSCAD `scale` parameter (see docs/TUTO_ECHELLES.md).
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout

from . import phoenix
from .profiles import SizingError, compute_kinetic_arm_sizing, compute_kinetic_sizing, compute_sizing

IMG = Path(__file__).resolve().parent / "assets" / "guide"
SCHEMA = Path(__file__).resolve().parent / "assets" / "schemas"

TX = {"fr": {"title": "Mettre à l'échelle la Phoenix : pas à pas", "close": "Fermer", "calc": "Calculateur rapide", "wrist": "Largeur du poignet mesurée :", "res": "Échelle : <b>{p:.2f} %</b> = ({w:g} + {m:g}) ÷ 43 × 100",
             "oob": "<span style='color:#b00020'><b>{p:.1f} %</b> : hors de la plage documentée (100–160 %, poignet de {lo:.1f} à {hi:.1f} mm). Rien n'est corrigé : revérifiez la mesure.</span>",
             "html": """<h2>1. Mesurer la largeur du poignet</h2>
<p>On mesure la <b>largeur du poignet de la main atteinte, à la ligne d'articulation</b> (le pli entre la main et l'avant-bras), en millimètres. Si vous pouvez rencontrer la personne, mesurez directement. Sinon, prenez une <b>photo de la main posée à plat sur une table</b>, avec à côté un mètre ou une carte bancaire.</p>
<p><img src="{schema}" width="520"></p>
<h2>2. Mesurer sur une photo (dans CustomLab)</h2>
<p>À l'étape « Mesures », le bouton <b>📷 Mesurer sur une photo</b> remplace l'outil externe d'autrefois :</p>
<ol><li>ouvrez la photo ;</li><li>choisissez la référence : <b>carte bancaire</b> (85,6 mm), feuille A4, ou mètre/règle ;</li><li>cliquez deux repères sur la référence (les deux coins de la carte, ou 10 cm et 20 cm sur un mètre) ;</li><li>cliquez les deux bords du poignet, sur la ligne d'articulation. Zoomez avec la molette pour placer les points précisément ;</li><li>« Utiliser cette mesure ».</li></ol>
<p><img src="{photo}" width="520"><br><i>Illustration dessinée (pas une vraie photo).</i></p>
<p><b>Attention :</b> photo de face, référence posée dans le même plan que le poignet. La perspective n'est pas corrigée : contrôlez la valeur avec un mètre ruban quand c'est possible.</p>
<h2>3. Ajouter 5 mm de confort et calculer le %</h2>
<p><b>Échelle (%) = (poignet + marge) ÷ 43 × 100</b>, avec une marge de <b>5 mm</b>. Les 43 mm sont la place disponible pour le poignet dans la main Phoenix à 100 %.</p>
<p>Exemple : un poignet de 40 mm donne (40 + 5) ÷ 43 × 100 = <b>104,65 %</b>. <b>CustomLab ajoute la marge tout seul : ne la rajoutez pas à la mesure.</b></p>
<p><img src="{mes}" width="620"></p>
<p>Cette règle vaut pour les mains Phoenix (et Raptor, Raptor Reloaded selon la page e-NABLE France). Dans CustomLab, la plage documentée est de <b>100 à 160 %</b> (poignet d'environ 38 à 63,8 mm) : hors plage, la valeur est refusée et jamais corrigée.</p>
<h2>4. Vérifier avant d'imprimer</h2>
<ul><li>La paume mise à l'échelle ne doit pas être très différente de la paume de la main valide de la personne.</li><li>Imprimez d'abord le <b>gabarit Phoenix</b> (rapide) ou la paume d'essai, et essayez-le sur le poignet.</li><li>Les règles ci-dessus restent à valider par un bénévole e-NABLE compétent : aucun essayage n'a été fait avec CustomLab.</li></ul>
<p style="color:#5b6b78"><small>Méthode d'après la page e-NABLE France « Mettre à l'échelle » : https://e-nable.fr/fr/fabrications/matching/mettre-a-lechelle/</small></p>"""},
      "en": {"title": "Scaling the Phoenix: step by step", "close": "Close", "calc": "Quick calculator", "wrist": "Measured wrist width:", "res": "Scale: <b>{p:.2f} %</b> = ({w:g} + {m:g}) ÷ 43 × 100",
             "oob": "<span style='color:#b00020'><b>{p:.1f} %</b>: outside the documented range (100–160 %, wrist {lo:.1f} to {hi:.1f} mm). Nothing is corrected: check the measurement.</span>",
             "html": """<h2>1. Measure the wrist width</h2><p>Measure the <b>width of the affected wrist at the joint line</b> (the crease between hand and forearm), in millimetres. If you can meet the person, measure directly; otherwise use a <b>photo of the hand lying flat on a table</b> with a ruler or a bank card beside it.</p>
<p><img src="{schema}" width="520"></p><h2>2. Measure on a photo (in CustomLab)</h2><p>In the "Measures" step, the <b>📷 Measure on a photo</b> button: open the photo, choose the reference (bank card 85.6 mm, A4 sheet or ruler), click two marks on it, click the two wrist edges (zoom with the wheel), then "Use this measure".</p>
<p><img src="{photo}" width="520"><br><i>Drawn illustration (not a real photo).</i></p><p><b>Note:</b> straight-on photo, reference in the same plane as the wrist; perspective is not corrected, check with a tape when possible.</p>
<h2>3. Add the 5 mm margin and compute the %</h2><p><b>Scale (%) = (wrist + margin) ÷ 43 × 100</b>, margin 5 mm; 43 mm is the room for the wrist in the Phoenix hand at 100 %. Example: 40 mm → (40 + 5) ÷ 43 × 100 = <b>104.65 %</b>. <b>CustomLab adds the margin itself: do not add it.</b></p>
<p><img src="{mes}" width="620"></p><p>CustomLab's documented range is <b>100–160 %</b> (wrist about 38–63.8 mm); outside it the value is refused, never corrected.</p>
<h2>4. Check before printing</h2><ul><li>The scaled palm should not differ much from the person's sound palm.</li><li>Print the Phoenix jig (gabarit) or a test palm first and try it on the wrist.</li><li>To be validated by a competent e-NABLE volunteer: no fitting has been done with CustomLab.</li></ul>
<p><small>Method after the e-NABLE France page "Mettre à l'échelle": https://e-nable.fr/fr/fabrications/matching/mettre-a-lechelle/</small></p>"""}}



# ---- other devices: HTML per language ({mes} = screenshot of the Measures step, {schema} = diagram when there is one)
KH = {"fr": """<h2>1. Mesurer (main atteinte)</h2>
<p>Méthode du manuel Kinetic Hand : photo de la main atteinte <b>à plat</b>, règle sur le bord de la table (l'outil « 📷 Mesurer sur une photo » de l'étape Mesures sert à ça), mesure <b>à la ligne de flexion du poignet</b>.</p>
<ul><li><b>Largeur du poignet</b> (obligatoire). <b>Ne pas ajouter de marge</b> : 3 mm de rembourrage sont ajoutés automatiquement.</li><li><b>Longueur de la paume</b> (obligatoire) : de la ligne du poignet à la partie la plus longue de la paume. Elle sert à choisir l'insert souple.</li><li>Facultatifs : largeur maximale de la paume ; longueur totale de la main saine (information seulement).</li></ul>
<h2>2. L'échelle</h2>
<p>Largeur du poignet + 3 mm → on prend la ligne la plus proche du <b>« Hand Scaling Chart »</b> du manuel (annexe 1) : de <b>50 à 100 %</b> par pas de 2,5 %. Entre deux lignes, on prend l'échelle supérieure. Le guide d'impression recommande <b>55 % minimum</b>. L'échelle est <b>uniforme</b>, pour toutes les pièces.</p>
<h2>3. L'insert souple A–E</h2>
<p>Espace libre dans la paume = longueur de paume du modèle (à cette échelle) − longueur mesurée → on prend l'insert le plus proche (A à E).</p>
<p><img src="{mes}" width="640"><br><i>Exemple du manuel reproduit : poignet 48 mm → 72,5 % + insert D (paume mesurée 40 mm).</i></p>
<h2>4. Main gauche et vérification</h2>
<ul><li>Toutes les pièces sont des mains droites : la main gauche est la <b>symétrie en X</b>, appliquée avant la décoration. CustomLab le fait seul.</li><li>Imprimez d'abord une <b>paume d'essai</b> et essayez-la avant de fabriquer la main.</li><li>À valider par un bénévole compétent : aucun essayage n'a été fait avec CustomLab.</li></ul>
<p><small>Source : manuel Kinetic Hand (Free 3D Hands, Mat Bowtell), annexe 1 « Hand Scaling Chart ». Voir aussi docs/KINETIC_HAND.md.</small></p>""",
"en": """<h2>1. Measure (affected hand)</h2><p>Kinetic Hand manual method: photo of the affected hand <b>flat</b>, ruler on the table edge (the "📷 Measure on a photo" tool does this), measured <b>at the wrist flexion line</b>.</p><ul><li><b>Wrist width</b> (required). <b>Do not add a margin</b>: 3 mm of padding is added automatically.</li><li><b>Palm length</b> (required): wrist line to the longest part of the palm; used to choose the soft insert.</li><li>Optional: maximum palm width; sound hand length (information only).</li></ul>
<h2>2. The scale</h2><p>Wrist width + 3 mm → nearest line of the manual's <b>Hand Scaling Chart</b> (appendix 1): <b>50 to 100 %</b> in 2.5 % steps; a tie goes to the larger scale. The print guide recommends <b>55 % minimum</b>. Uniform scale for all parts.</p>
<h2>3. Soft insert A–E</h2><p>Free room in the palm = model palm length (at that scale) − measured length → nearest insert.</p><p><img src="{mes}" width="640"><br><i>Manual example reproduced: wrist 48 mm → 72.5 % + insert D (palm 40 mm).</i></p>
<h2>4. Left hand and checks</h2><ul><li>All parts are right hands: the left hand is the X mirror, applied before decoration (automatic).</li><li>Print a <b>test palm</b> first.</li><li>To be validated by a competent volunteer: no fitting done with CustomLab.</li></ul><p><small>Source: Kinetic Hand manual (Free 3D Hands, Mat Bowtell), appendix 1. See docs/KINETIC_HAND.md.</small></p>"""}
KA = {"fr": """<h2>1. Les 3 mesures (manuel Kinetic Arm, étape 2)</h2>
<ul><li><b>Longueur de la main saine</b> : du bout du majeur au poignet.</li><li><b>Largeur du coude</b> du membre résiduel : la partie la plus large, souvent au pli.</li><li><b>Longueur du membre résiduel</b> : de l'olécrâne à l'extrémité.</li><li>Facultatif : longueur de l'avant-bras valide, pour un contrôle (le membre résiduel doit faire 15 à 70 % de l'avant-bras valide).</li></ul>
<h2>2. Du chiffre aux pièces (pages 28–33, tableaux B1 à B4)</h2>
<ol><li>Longueur de la main saine → <b>échelle des composants inférieurs</b> (arrondie vers le <b>bas</b> ; 50 à 100 %).</li><li>Largeur du coude → <b>type d'avant-bras A à F</b> (arrondie vers le <b>haut</b>).</li><li>(échelle inférieure, type) → <b>échelle des composants supérieurs</b>.</li><li>Longueur du membre résiduel → <b>insert A à Q</b> (arrondie vers le haut).</li><li>(insert, type) → <b>languette 1 à 4</b> et <b>doublure néoprène</b> (jeu 1 à 12).</li></ol>
<p><img src="{mes}" width="640"></p>
<h2>3. Fichiers pré-échelonnés</h2>
<p>Paume, mécanisme de verrouillage et tendeurs existent en plusieurs échelles : on prend <b>le bon fichier</b>, qu'on ne met <b>jamais à l'échelle dans le trancheur</b>. CustomLab choisit le fichier et prévient si l'échelle ne correspond pas exactement (les tendeurs existent par pas de 2,5 %).</p>
<h2>4. Vérifier</h2>
<ul><li>Imprimez d'abord un <b>bras d'essai</b> (bras supérieur, charnières de coude, avant-bras).</li><li>Un changement d'échelle doit être revu par un <b>professionnel de santé</b> (manuel).</li><li><b>Les tableaux B1 à B3 ont été recopiés depuis des images</b> : un bénévole doit en relire quelques lignes.</li></ul>
<p><small>Source : Kinetic Arm Assembly Manual (Free 3D Hands, Mat Bowtell). Voir docs/KINETIC_ARM.md.</small></p>""",
"en": """<h2>1. The 3 measurements (Kinetic Arm manual, step 2)</h2><ul><li><b>Sound hand length</b>: middle fingertip to wrist.</li><li><b>Elbow width</b> of the residual limb: widest part, often at the crease.</li><li><b>Residual limb length</b>: olecranon to the end.</li><li>Optional: sound forearm length, for a check (residual limb = 15–70 % of it).</li></ul>
<h2>2. From numbers to parts (pages 28–33, tables B1–B4)</h2><ol><li>Sound hand length → <b>lower components scale</b> (rounded <b>down</b>; 50–100 %).</li><li>Elbow width → <b>forearm type A–F</b> (rounded <b>up</b>).</li><li>(lower scale, type) → <b>upper components scale</b>.</li><li>Residual limb length → <b>insert A–Q</b> (rounded up).</li><li>(insert, type) → <b>tongue 1–4</b> and <b>neoprene liner</b> (set 1–12).</li></ol><p><img src="{mes}" width="640"></p>
<h2>3. Pre-scaled files</h2><p>Palm, locking mechanism and tensioners exist in several scales: take <b>the right file</b>, <b>never scale it in the slicer</b>. CustomLab picks it and warns when the scale is not exact.</p>
<h2>4. Check</h2><ul><li>Print a <b>test arm</b> first.</li><li>A change of scale must be reviewed by an <b>allied-health professional</b> (manual).</li><li><b>Tables B1–B3 were copied from images</b>: a volunteer should proof-read some rows.</li></ul><p><small>Source: Kinetic Arm Assembly Manual (Free 3D Hands, Mat Bowtell). See docs/KINETIC_ARM.md.</small></p>"""}
UA = {"fr": """<h2>1. Les 3 mesures (page e-NABLE France « Prise de mesures du destinataire »)</h2>
<p>Pour le bras Unlimbited, trois mesures sont nécessaires. Attention : <b>deux sont prises sur le bras NON atteint</b>, une seule sur le bras atteint.</p>
<ul><li><b>C — longueur de la main NON atteinte</b> (paramètre <b>HandLen</b>) : du poignet à l'extrémité du doigt le plus long. De 135 à 230 mm.</li><li><b>B — longueur de l'avant-bras NON atteint</b> (<b>ForearmLen</b>) : du pli interne du coude au poignet. De 120 à 315 mm.</li><li><b>A — circonférence du bras ATTEINT</b> (<b>BicepCircum</b>) : mesurée à partir du milieu du bras. De 110 à 350 mm. C'est bien le bras pour lequel on construit l'appareil, pas celui qui sert aux autres mesures.</li></ul>
<p><img src="{schema}" width="460"></p>
<h2>2. Ce que calcule le SCAD</h2>
<p>Échelle de la main : <b>HandPerc = arrondi(HandLen ÷ 135 × 100)</b>. Paume, doigts, phalanges et broches suivent cette échelle ; avant-bras, manchette et gabarit sont paramétrés par les trois mesures. 135 mm est le <b>minimum pour la sécurité des enfants</b> (petites pièces, tolérance des broches).</p>
<p><img src="{mes}" width="640"></p>
<h2>3. Générer les pièces</h2>
<ul><li>Il faut le <b>fichier SCAD officiel</b> (Aide → Fichiers sources) et OpenSCAD.</li><li>Chaque pièce se <b>génère</b> (1 seconde pour les petites, jusqu'à 5 minutes pour l'avant-bras). Si les mesures changent, régénérez avant d'exporter.</li></ul>
<h2>4. Vérifier</h2><ul><li>Imprimez d'abord les petites pièces et essayez-les ; à valider par un bénévole e-NABLE compétent.</li><li>Licence CC BY-NC-SA : les dérivés se partagent sous la même licence.</li></ul>
<p><small>Sources : page e-NABLE France « Prise de mesures du destinataire » ; SCAD officiel UnLimbited Arm v2.1 (thing 1672381). Voir docs/UNLIMBITED_ARM.md.</small></p>""",
"en": """<h2>1. The 3 measurements (e-NABLE France page "Prise de mesures du destinataire")</h2><p>Three measurements are needed. Note: <b>two are taken on the NON-affected arm</b>, only one on the affected arm.</p><ul><li><b>C — NON-affected hand length</b> (<b>HandLen</b>): wrist to the tip of the longest finger. 135–230 mm.</li><li><b>B — NON-affected forearm length</b> (<b>ForearmLen</b>): inner elbow crease to wrist. 120–315 mm.</li><li><b>A — AFFECTED arm circumference</b> (<b>BicepCircum</b>): measured at the middle of the arm. 110–350 mm. It is the arm the device is built for, not the one used for the other measures.</li></ul><p><img src="{schema}" width="460"></p>
<h2>2. What the SCAD computes</h2><p>Hand scale: <b>HandPerc = round(HandLen ÷ 135 × 100)</b>. Palm, fingers, phalanges and pins follow it; forearm, cuff and jig use the three measurements. 135 mm is the <b>minimum for children's safety</b>.</p><p><img src="{mes}" width="640"></p>
<h2>3. Generate the parts</h2><ul><li>You need the <b>official SCAD</b> (Help → Source files) and OpenSCAD.</li><li>Each part is <b>generated</b> (1 s to 5 min). If the measures change, regenerate before exporting.</li></ul>
<h2>4. Check</h2><ul><li>Print the small parts first; to be validated by a competent e-NABLE volunteer.</li><li>CC BY-NC-SA: derivatives must be shared under the same licence.</li></ul><p><small>Sources: e-NABLE France page "Prise de mesures du destinataire"; official UnLimbited Arm v2.1 SCAD (thing 1672381). See docs/UNLIMBITED_ARM.md.</small></p>"""}
HTML = {"phoenix_hand": None, "kinetic_hand": KH, "kinetic_arm": KA, "unlimbited_arm": UA}
TITLES = {"phoenix_hand": ("Phoenix", "Phoenix"), "kinetic_hand": ("Kinetic Hand", "Kinetic Hand"), "kinetic_arm": ("Kinetic Arm", "Kinetic Arm"), "unlimbited_arm": ("Unlimbited Arm", "Unlimbited Arm")}
# calculators: (field id, label fr, label en, default, min, max)
CALC = {"kinetic_hand": [("wrist_mm", "Largeur du poignet", "Wrist width", 48.0, 1, 200), ("palm_mm", "Longueur de la paume", "Palm length", 40.0, 1, 200)],
        "kinetic_arm": [("hand_mm", "Longueur de la main saine", "Sound hand length", 180.0, 1, 400), ("elbow_mm", "Largeur du coude", "Elbow width", 60.0, 1, 200), ("resid_mm", "Longueur du membre résiduel", "Residual limb length", 150.0, 1, 500)],
        "unlimbited_arm": [("HandLen", "C — main NON atteinte (HandLen)", "C — NON-affected hand (HandLen)", 180.0, 1, 400), ("ForearmLen", "B — avant-bras NON atteint (ForearmLen)", "B — NON-affected forearm (ForearmLen)", 220.0, 1, 500), ("BicepCircum", "A — bras ATTEINT, circonférence (BicepCircum)", "A — AFFECTED arm circumference (BicepCircum)", 250.0, 1, 500)]}


def calc_html(device, vals, lang):
    """Result of the app's own sizing function for the typed values (HTML); the error text when a value is refused (nothing is corrected)."""
    fr = lang == "fr"
    try:
        if device == "kinetic_hand":
            r = compute_kinetic_sizing("right", "", vals["wrist_mm"], vals["palm_mm"]); d = r.derived
            return (f"Échelle : <b>{d['scale_percent']:g} %</b> · poignet + 3 mm = {d['padded_wrist_mm']:g} mm · insert <b>{d['insert']}</b>" if fr else f"Scale: <b>{d['scale_percent']:g} %</b> · wrist + 3 mm = {d['padded_wrist_mm']:g} mm · insert <b>{d['insert']}</b>")
        if device == "kinetic_arm":
            r = compute_kinetic_arm_sizing("right", vals["hand_mm"], vals["elbow_mm"], vals["resid_mm"]); d = r.derived
            return (f"Inférieurs <b>{d['lower_scale']:g} %</b> · avant-bras <b>{d['forearm_type']}</b> · supérieurs <b>{d['upper_scale']:g} %</b> · insert <b>{d['insert']}</b> · languette {d['tongue']} · doublure {d['liner_set']}" if fr
                    else f"Lower <b>{d['lower_scale']:g} %</b> · forearm <b>{d['forearm_type']}</b> · upper <b>{d['upper_scale']:g} %</b> · insert <b>{d['insert']}</b> · tongue {d['tongue']} · liner {d['liner_set']}")
        if device == "unlimbited_arm":
            r = compute_sizing("unlimbited_arm", "right", "Palm", dict(vals)); return f"HandPerc = <b>{r.derived['HandPerc']} %</b> (HandLen ÷ 135 × 100)"
    except (SizingError, ValueError) as e:
        return f"<span style='color:#b00020'>{str(e)[:300]}</span>"
    return ""


class ScaleGuideDialog(QDialog):
    def __init__(self, parent, lang, device="phoenix_hand", values=None):
        super().__init__(parent); self.lang, self.device = lang, device if device in HTML else "phoenix_hand"; self.t = TX[lang]
        pre = "Mettre à l'échelle : " if lang == "fr" else "Scaling: "; post = " : pas à pas" if lang == "fr" else " : step by step"
        self.setWindowTitle(self.t["title"] if self.device == "phoenix_hand" else pre + TITLES[self.device][0] + post); self.resize(840, 780)
        v = QVBoxLayout(self); v.addWidget(QLabel(f"<b>{self.t['calc']}</b>")); self.spins = {}
        row = QHBoxLayout()
        if self.device == "phoenix_hand":
            w = (values or {}).get("wrist_mm") or 40.0; row.addWidget(QLabel(self.t["wrist"])); self.spin = QDoubleSpinBox(); self.spin.setRange(1, 300); self.spin.setDecimals(1); self.spin.setSuffix(" mm"); self.spin.setValue(w)
            self.spin.valueChanged.connect(self.calc); row.addWidget(self.spin)
        else:
            for fid, lfr, len_, dflt, lo, hi in CALC[self.device]:
                sp = QDoubleSpinBox(); sp.setRange(lo, hi); sp.setDecimals(1); sp.setSuffix(" mm"); sp.setValue((values or {}).get(fid) or dflt); sp.valueChanged.connect(self.calc)
                self.spins[fid] = sp; col = QVBoxLayout(); col.addWidget(QLabel(lfr if lang == "fr" else len_)); col.addWidget(sp); row.addLayout(col)
        v.addLayout(row); self.out = QLabel(); self.out.setTextFormat(Qt.RichText); self.out.setWordWrap(True); v.addWidget(self.out)
        self.view = QTextBrowser(); self.view.setOpenExternalLinks(False)
        img = {"schema": (SCHEMA / ("bras_%s.svg" % lang)).as_uri(), "photo": (IMG / "outil_photo.png").as_uri(), "mes": (IMG / f"mesures_{self.device}.png").as_uri()}
        if self.device == "phoenix_hand": img["schema"] = (SCHEMA / f"poignet_{lang}.svg").as_uri(); html = self.t["html"]
        else: html = HTML[self.device][lang]
        self.view.setHtml(html.format(**img)); v.addWidget(self.view, 1)
        r2 = QHBoxLayout(); r2.addStretch(1); b = QPushButton(self.t["close"]); b.clicked.connect(self.close); r2.addWidget(b); v.addLayout(r2); self.calc()

    def calc(self, *_):
        if self.device != "phoenix_hand": self.out.setText(calc_html(self.device, {k: s.value() for k, s in self.spins.items()}, self.lang)); return
        w = self.spin.value(); p = phoenix.scale_percent(w); lo, hi = phoenix.wrist_range_mm()
        self.out.setText(self.t["res"].format(p=p, w=w, m=phoenix.DEFAULT_MARGIN_MM) if phoenix.SCALE_MIN <= p <= phoenix.SCALE_MAX else self.t["oob"].format(p=p, lo=lo, hi=hi))
