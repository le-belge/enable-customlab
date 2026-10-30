"""Plain-language, bilingual messages with a severity level.

Source texts come from the engines (profiles.py, phoenix.py, deco.py). Each rule recognises a source message (in either
language) and returns it in the requested language with a severity:
  block = prevents the action, check = needs a human check, info = good to know.
Unknown messages are kept verbatim (severity from the caller) so nothing is ever hidden.
"""
import re

BLOCK, CHECK, INFO = "block", "check", "info"
ICON = {BLOCK: "✖", CHECK: "⚠", INFO: "ℹ"}
COLOR = {BLOCK: "#b00020", CHECK: "#8a4b00", INFO: "#0b314d"}

# (regex on the source text, severity, FR template, EN template or None = keep source)
RULES = [
    # ---- sizing / profiles / Phoenix formula
    (r"^Print the verification jig", INFO, "Imprimez d'abord le gabarit Phoenix et comparez la paume mise à l'échelle avec la paume valide du bénéficiaire.", "Print the Phoenix verification jig first and compare the scaled palm with the recipient's sound palm."),
    (r"^EXPERIMENTAL: dimensional compatibility", CHECK, "Dimensionnement EXPÉRIMENTAL : la compatibilité n'est pas validée et aucune conformité n'est affirmée.", "EXPERIMENTAL sizing: compatibility is not validated and no conformity is claimed."),
    (r"^Licence depends on the file variant", INFO, "La licence dépend des fichiers utilisés ; elle est recopiée dans la fiche d'export.", "The licence depends on the files used; it is copied into the export sheet."),
    (r"^Licence not verified", CHECK, "Licence non vérifiée sur la source d'origine.", "Licence not verified on the original source."),
    (r"^Scale close to the limit", CHECK, "L'échelle est proche de la limite de la plage documentée.", "The scale is close to the limit of the documented range."),
    (r"^Margin ([\d.]+) mm differs", CHECK, "La marge ({0} mm) diffère des 5 mm recommandés.", "The margin ({0} mm) differs from the recommended 5 mm."),
    (r"^(\w+): no documented valid range", INFO, "{0} : aucune plage valide n'est documentée, la valeur n'est pas contrôlée.", "{0}: no valid range is documented, the value is not checked."),
    (r"^Measurement label mapping not confirmed", CHECK, "L'association entre les mesures et les lettres A/C n'est pas confirmée par les sources.", "The mapping between the measurements and the letters A/C is not confirmed by the sources."),
    (r"^Scale ([\d.]+) % is (?:below 100 %|above 160 %).*?With a ([\d.]+) mm margin the usable wrist width is ([\d.]+)-([\d.]+) mm", BLOCK,
     "Échelle de {0} % hors de la plage documentée (100–160 %). Avec une marge de {1} mm, la largeur de poignet utilisable est de {2} à {3} mm. Rien n'a été modifié : vérifiez la mesure, la marge ou choisissez un autre appareil.",
     "A scale of {0} % is outside the documented range (100–160 %). With a {1} mm margin the usable wrist width is {2} to {3} mm. Nothing was changed: check the measurement, the margin, or choose another device."),
    (r"^(\w+): must be > 0", BLOCK, "{0} : la valeur doit être supérieure à 0.", "{0}: the value must be greater than 0."),
    (r"^(\w+)=([\d.]+)mm outside documented range ([\d.]+)-([\d.]+)", BLOCK, "{0} = {1} mm hors de la plage documentée ({2}–{3}).", "{0} = {1} mm is outside the documented range ({2}–{3})."),
    (r"^Residual limb = ([\d.]+) % of sound forearm \(documented suitable range (\d+)-(\d+) %\)", INFO, "Le moignon représente {0} % de l'avant-bras valide (plage documentée : {1}–{2} %).", None),
    (r"^Wrist width ([\d.]+) mm \+ ([\d.]+) mm of padding = ([\d.]+) mm is outside the Hand Scaling Chart \(([\d.]+)-([\d.]+) mm", BLOCK,
     "Poignet de {0} mm + {1} mm de rembourrage = {2} mm : hors du tableau de dimensionnement du manuel ({3} à {4} mm, échelles 50 à 100 %). Rien n'a été modifié : vérifiez la mesure.",
     "Wrist width {0} mm + {1} mm of padding = {2} mm is outside the manual's scaling chart ({3} to {4} mm, scales 50 to 100 %). Nothing was changed: check the measurement."),
    (r"^(\w+): a positive number \(mm\) is required", BLOCK, "{0} : saisissez un nombre positif (mm).", "{0}: enter a positive number (mm)."),
    (r"^Scale ([\d.]+) % is below the 55 %", CHECK, "L'échelle de {0} % est sous les 55 % que le guide d'impression donne comme minimum pour la main d'un petit enfant (le tableau descend à 50 %).", "A scale of {0} % is below the 55 % that the printing guide gives as the minimum for a small child's hand (the chart goes down to 50 %)."),
    (r"^The measured palm length \(([\d.]+) mm\) is longer than the design palm at ([\d.]+) % \(([\d.]+) mm\)", CHECK, "La paume mesurée ({0} mm) est plus longue que celle du modèle à {1} % ({2} mm) : aucun insert ne peut combler un espace négatif. Imprimez une paume d'essai et envisagez une variante de paume.", "The measured palm ({0} mm) is longer than the design palm at {1} % ({2} mm): no insert can fill a negative space. Print a test palm and consider a palm variant."),
    (r"^No insert fits the ([-\d.]+) mm of free palm space well \(closest: insert (\w) = (\d+) mm\)", CHECK, "Aucun insert ne convient bien aux {0} mm d'espace libre dans la paume (le plus proche : insert {1} = {2} mm).", "No insert fits the {0} mm of free palm space well (closest: insert {1} = {2} mm)."),
    (r"^The measured maximum palm width \+ padding \(([\d.]+) mm\) exceeds the design at ([\d.]+) % \(([\d.]+) mm\)", CHECK, "La largeur maximale de paume mesurée + rembourrage ({0} mm) dépasse celle du modèle à {1} % ({2} mm) : la paume risque d'être trop étroite.", "The measured maximum palm width + padding ({0} mm) exceeds the design at {1} % ({2} mm): the palm may be too narrow."),
    (r"^Print a test palm and check the fit", INFO, "Imprimez une paume d'essai et vérifiez l'ajustement avant d'assembler une main pour un bénéficiaire (manuel, page de la paume d'essai).", "Print a test palm and check the fit before assembling a hand for a recipient (manual, test palm page)."),
    (r"^Basic scaling gives an overall hand length of ([\d.]+) mm, ([+-][\d.]+) mm from the sound hand \(([\d.]+) mm\)", INFO, "L'échelle de base donne une main de {0} mm de long, soit {1} mm par rapport à la main saine ({2} mm).", "Basic scaling gives an overall hand length of {0} mm, {1} mm from the sound hand ({2} mm)."),
    (r"^Sizing is unavailable|^Dimensionnement indisponible", BLOCK, "Dimensionnement indisponible pour cet appareil : voir le blocage ci-dessus.", "Sizing is unavailable for this device: see the blocker above."),
    # ---- decoration (source language: French)
    (r"^Décoration vide ou hors de la zone affichée", BLOCK, "Aucun motif dans la zone affichée : saisissez un texte ou choisissez un fichier, ou replacez le motif.", "No motif in the displayed area: enter a text or choose a file, or move the motif."),
    (r"^(\d+) cellules de la décoration dépassent de la pièce", BLOCK, "Le motif déborde de la pièce ou survole un vide ({0} points) : réduisez-le ou déplacez-le.", "The motif extends past the part or over a gap ({0} points): make it smaller or move it."),
    (r"^Profondeur ([\d.]+) mm hors limites logicielles ([\d.]+)-([\d.]+) mm \((\w+)\)", BLOCK, "Profondeur de {0} mm refusée : le logiciel accepte {1} à {2} mm pour ce mode (limite de prudence du logiciel, pas une règle e-NABLE).", "A depth of {0} mm is refused: the software accepts {1} to {2} mm for this mode (a precaution of this software, not an e-NABLE rule)."),
    (r"^(Gravure|Incrustation) ([\d.]+) mm > (\d+) % de l'épaisseur .*?\(([\d.]+) mm\)", BLOCK, "Profondeur de {1} mm trop forte : la pièce ne fait que {3} mm d'épaisseur à cet endroit (maximum {2} % de l'épaisseur).", "A depth of {1} mm is too deep: the part is only {3} mm thick here (maximum {2} % of the thickness)."),
    (r"^La décoration entre dans la zone interdite n°(\d+) \((\d+) cellules\)", BLOCK, "Le motif entre dans la zone interdite n°{0} que vous avez tracée.", "The motif enters the forbidden zone no. {0} that you drew."),
    (r"^La décoration entre dans la zone protégée automatiquement", BLOCK, "Le motif touche une zone protégée automatiquement (autour d'un trou ou d'une fente, ou bord trop pentu) : déplacez-le ou réduisez la marge.", "The motif touches an automatically protected area (around a hole or slot, or a steep rim): move it or reduce the margin."),
    (r"^Pente locale (\d+)° > (\d+)°", BLOCK, "La surface est trop inclinée sous le motif ({0}° au maximum {1}°) : il serait déformé. Choisissez une zone plus plane.", "The surface is too steep under the motif ({0}°, maximum {1}°): it would be distorted. Choose a flatter area."),
    (r"^Pente locale jusqu'à (\d+)° sous le motif", CHECK, "La surface est inclinée jusqu'à {0}° sous le motif : le rendu peut être légèrement déformé.", "The surface slopes up to {0}° under the motif: the result may be slightly distorted."),
    (r"^(\d+) % du motif est plus fin que ([\d.]+) mm", CHECK, "{0} % du motif est plus fin que {1} mm (deux fois la buse de 0,4) : ces traits fins risquent de ne pas s'imprimer. Agrandissez ou simplifiez le motif.", "{0} % of the motif is thinner than {1} mm (twice the 0.4 nozzle): these fine lines may not print. Enlarge or simplify the motif."),
    (r"^Des fentes/espaces plus étroits que ([\d.]+) mm .*?(\d+) %", CHECK, "Des espaces plus étroits que {0} mm ({1} % de la surface du motif) risquent de se refermer à l'impression.", "Gaps narrower than {0} mm ({1} % of the motif area) may close up when printing."),
    (r"^Zones fonctionnelles non détectées automatiquement", CHECK, "Les zones fonctionnelles autres que les trous ne sont pas détectées : vérifiez à la main qu'aucune articulation, trou de broche, passage de câble ou surface de contact n'est touché.", "Functional areas other than holes are not detected: check by hand that no joint, pin hole, cable path or skin-contact surface is touched."),
    (r"^Incrustation en couleurs", INFO, "Incrustation en couleurs : ouvrez le fichier « …_Bambu_pret.3mf » (pièces et filaments déjà assignés). Le blanc du motif reste dans la couleur de la base.", "Colour inlay: open the “…_Bambu_pret.3mf” file (parts and filaments already assigned). The white of the motif stays in the base colour."),
    (r"^Incrustation :", INFO, "Incrustation : ouvrez le fichier « …_Bambu_pret.3mf » (pièces et filaments déjà assignés). Affleurant à environ 0,03 mm près, non vérifié à l'impression.", "Inlay: open the “…_Bambu_pret.3mf” file (parts and filaments already assigned). Flush to about 0.03 mm, not checked by printing."),
    (r"^Relief en couleurs", INFO, "Relief en couleurs : une pièce par couleur, à charger avec la pièce d'origine ; un filament par couleur.", "Colour relief: one part per colour, to load with the original part; one filament per colour."),
    (r"^Gravure impossible", BLOCK, "Gravure impossible sur cette pièce : elle n'est pas étanche, la soustraction ne serait pas fiable. Utilisez le relief ou l'incrustation.", "Engraving is not possible on this part: it is not watertight, so subtraction would be unreliable. Use relief or inlay."),
    (r"^\(aucune décoration\)", INFO, "Aucune décoration : la pièce d'origine sera exportée telle quelle.", "No decoration: the original part will be exported unchanged."),
    (r"^Échelle demandée mais non calculable", BLOCK, "Échelle demandée mais non calculable : saisissez la largeur du poignet (étape 2) ou décochez l'option.", "A scale is requested but cannot be computed: enter the wrist width (step 2) or untick the option."),
    (r"^Mesures manquantes ou hors plage", BLOCK, "Mesures manquantes ou hors plage : corrigez-les à l'étape 2.", "Missing or out-of-range measures: fix them in step 2."),
    (r"^La pièce générée ne correspond pas", BLOCK, "La pièce générée ne correspond pas aux mesures actuelles : générez-la à l'étape 3.", "The generated part does not match the current measures: generate it in step 3."),
    (r"^Choisissez d'abord|^Choose the part", BLOCK, "Choisissez d'abord la pièce à l'étape 3.", "Choose the part in step 3 first."),
]
_COMPILED = [(re.compile(p, re.S), sev, fr, en) for p, sev, fr, en in RULES]


def localize(text, lang="fr", default=CHECK):
    """-> (severity, text, matched). Unmatched texts are returned unchanged with `default` severity."""
    t = (text or "").strip()
    for rx, sev, fr, en in _COMPILED:
        m = rx.search(t)
        if m:
            tpl = fr if lang == "fr" else (en if en is not None else t)
            try: return sev, tpl.format(*m.groups()), True
            except (IndexError, KeyError): return sev, t, True
    return default, t, False


def sort_messages(items, lang="fr", default=CHECK):
    """items: [(text, default_severity|None)] -> [(severity, localized)] ordered block, check, info, de-duplicated."""
    order = {BLOCK: 0, CHECK: 1, INFO: 2}; out, seen = [], set()
    for it in items:
        text, dflt = (it if isinstance(it, tuple) else (it, None))
        sev, loc, _ = localize(text, lang, dflt or default)
        if loc and loc not in seen: seen.add(loc); out.append((sev, loc))
    return sorted(out, key=lambda x: order[x[0]])


def messages_html(items, lang="fr", default=CHECK):
    rows = [f"<p style='margin:2px 0;color:{COLOR[s]}'>{ICON[s]} {t}</p>" for s, t in sort_messages(items, lang, default)]
    return "".join(rows)
