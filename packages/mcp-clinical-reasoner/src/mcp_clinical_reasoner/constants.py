"""Static reference tables for mcp-clinical-reasoner.

- DOSE_TABLE      — rule-based max dose info for ~20 common drugs
- ALLERGEN_CLASSES — drug cross-reactivity groups
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Dose table
# Keys: lowercase drug name (primary key used for lookups).
# Dose values are in mg unless noted.
# DISCLAIMER: These are general adult reference ranges from standard references
# (FDA labels, Lexi-Comp, Clinical Pharmacology). Individual patient dosing
# must always be verified by a licensed prescriber or pharmacist.
# ---------------------------------------------------------------------------
DOSE_TABLE: dict[str, dict] = {
    "acetaminophen": {
        "rxcui": "161",
        "aliases": ["paracetamol", "tylenol", "apap"],
        "max_single_dose_mg": 1000.0,
        "max_daily_dose_mg": 4000.0,
        "typical_adult_dose_mg": 500.0,
        "routes": ["oral", "rectal", "iv"],
        "notes": (
            "Hepatotoxicity risk >4000 mg/day; limit to 3000 mg/day in patients "
            "with hepatic disease or regular alcohol use."
        ),
    },
    "ibuprofen": {
        "rxcui": "5640",
        "aliases": ["advil", "motrin", "nuprin"],
        "max_single_dose_mg": 800.0,
        "max_daily_dose_mg": 3200.0,
        "typical_adult_dose_mg": 400.0,
        "routes": ["oral"],
        "notes": (
            "OTC max: 1200 mg/day. Rx max: 3200 mg/day. Take with food. "
            "Avoid in renal impairment, active peptic ulcer, or late pregnancy."
        ),
    },
    "aspirin": {
        "rxcui": "1191",
        "aliases": ["asa", "acetylsalicylic acid", "ecotrin"],
        "max_single_dose_mg": 1000.0,
        "max_daily_dose_mg": 4000.0,
        "typical_adult_dose_mg": 325.0,
        "routes": ["oral", "rectal"],
        "notes": (
            "Antiplatelet: 81 mg/day. Analgesic/antipyretic: 325–1000 mg q4–6h. "
            "Avoid in children with viral illness (Reye's syndrome risk)."
        ),
    },
    "naproxen": {
        "rxcui": "7258",
        "aliases": ["aleve", "naprosyn", "anaprox"],
        "max_single_dose_mg": 500.0,
        "max_daily_dose_mg": 1500.0,
        "typical_adult_dose_mg": 250.0,
        "routes": ["oral"],
        "notes": (
            "OTC: 220 mg q8–12h, max 660 mg/day. Rx: 250–500 mg bid, max 1500 mg/day. "
            "Longer half-life than ibuprofen; less frequent dosing."
        ),
    },
    "metformin": {
        "rxcui": "6809",
        "aliases": ["glucophage", "glumetza"],
        "max_single_dose_mg": 1000.0,
        "max_daily_dose_mg": 2550.0,
        "typical_adult_dose_mg": 500.0,
        "routes": ["oral"],
        "notes": (
            "Start 500–850 mg/day with meals; titrate slowly. "
            "Contraindicated if eGFR < 30 mL/min/1.73m². Withhold before contrast."
        ),
    },
    "lisinopril": {
        "rxcui": "29046",
        "aliases": ["prinivil", "zestril"],
        "max_single_dose_mg": 40.0,
        "max_daily_dose_mg": 40.0,
        "typical_adult_dose_mg": 10.0,
        "routes": ["oral"],
        "notes": (
            "HTN: 10–40 mg/day. Heart failure: 5–40 mg/day. "
            "Reduce dose in renal impairment. Monitor potassium and creatinine."
        ),
    },
    "atorvastatin": {
        "rxcui": "83367",
        "aliases": ["lipitor"],
        "max_single_dose_mg": 80.0,
        "max_daily_dose_mg": 80.0,
        "typical_adult_dose_mg": 20.0,
        "routes": ["oral"],
        "notes": (
            "Take once daily. Max 40 mg/day with certain CYP3A4 inhibitors "
            "(clarithromycin, itraconazole). Monitor for myopathy."
        ),
    },
    "metoprolol": {
        "rxcui": "41493",
        "aliases": ["lopressor", "toprol-xl", "toprol xl"],
        "max_single_dose_mg": 200.0,
        "max_daily_dose_mg": 400.0,
        "typical_adult_dose_mg": 50.0,
        "routes": ["oral"],
        "notes": (
            "HTN: 50–200 mg/day. Tachyarrhythmia control: up to 400 mg/day. "
            "Do not abruptly discontinue; taper over 1–2 weeks."
        ),
    },
    "amlodipine": {
        "rxcui": "17767",
        "aliases": ["norvasc"],
        "max_single_dose_mg": 10.0,
        "max_daily_dose_mg": 10.0,
        "typical_adult_dose_mg": 5.0,
        "routes": ["oral"],
        "notes": (
            "Once daily. Max 10 mg/day. Start 2.5–5 mg in elderly or hepatic impairment. "
            "Peripheral oedema is common adverse effect."
        ),
    },
    "omeprazole": {
        "rxcui": "7646",
        "aliases": ["prilosec", "losec"],
        "max_single_dose_mg": 40.0,
        "max_daily_dose_mg": 80.0,
        "typical_adult_dose_mg": 20.0,
        "routes": ["oral", "iv"],
        "notes": (
            "GERD: 20–40 mg/day. H. pylori eradication: 20–40 mg bid. "
            "Pathological hypersecretory conditions: up to 120 mg/day (split doses)."
        ),
    },
    "amoxicillin": {
        "rxcui": "723",
        "aliases": ["amoxil", "trimox"],
        "max_single_dose_mg": 1000.0,
        "max_daily_dose_mg": 3000.0,
        "typical_adult_dose_mg": 500.0,
        "routes": ["oral"],
        "notes": (
            "Standard: 500 mg q8h or 875 mg q12h. "
            "Penicillin-class antibiotic; check for penicillin allergy first."
        ),
    },
    "azithromycin": {
        "rxcui": "18631",
        "aliases": ["zithromax", "zpack", "z-pack"],
        "max_single_dose_mg": 500.0,
        "max_daily_dose_mg": 500.0,
        "typical_adult_dose_mg": 500.0,
        "routes": ["oral", "iv"],
        "notes": (
            "Z-pack: 500 mg day 1, then 250 mg days 2–5. "
            "Avoid in prolonged QT or concurrent QT-prolonging drugs."
        ),
    },
    "warfarin": {
        "rxcui": "11289",
        "aliases": ["coumadin", "jantoven"],
        "max_single_dose_mg": 20.0,
        "max_daily_dose_mg": 20.0,
        "typical_adult_dose_mg": 5.0,
        "routes": ["oral"],
        "notes": (
            "Dose highly variable; individualize to INR target (usually 2–3). "
            "Numerous drug/food interactions. Narrow therapeutic index."
        ),
    },
    "furosemide": {
        "rxcui": "4603",
        "aliases": ["lasix"],
        "max_single_dose_mg": 600.0,
        "max_daily_dose_mg": 600.0,
        "typical_adult_dose_mg": 40.0,
        "routes": ["oral", "iv"],
        "notes": (
            "Edema: 20–80 mg/day initially, titrate as needed. "
            "HTN: 40–80 mg/day. Sulfonamide structure — check sulfa allergy."
        ),
    },
    "sertraline": {
        "rxcui": "36437",
        "aliases": ["zoloft"],
        "max_single_dose_mg": 200.0,
        "max_daily_dose_mg": 200.0,
        "typical_adult_dose_mg": 50.0,
        "routes": ["oral"],
        "notes": (
            "Start 25–50 mg/day; titrate by 25–50 mg/week. Max 200 mg/day. "
            "Allow 2 weeks before assessing response."
        ),
    },
    "gabapentin": {
        "rxcui": "25480",
        "aliases": ["neurontin"],
        "max_single_dose_mg": 1200.0,
        "max_daily_dose_mg": 3600.0,
        "typical_adult_dose_mg": 300.0,
        "routes": ["oral"],
        "notes": (
            "Epilepsy: 900–3600 mg/day in three divided doses. "
            "Neuropathic pain: 300–3600 mg/day. Renal dose adjustment required."
        ),
    },
    "clopidogrel": {
        "rxcui": "32968",
        "aliases": ["plavix"],
        "max_single_dose_mg": 600.0,
        "max_daily_dose_mg": 600.0,
        "typical_adult_dose_mg": 75.0,
        "routes": ["oral"],
        "notes": (
            "Maintenance: 75 mg/day. ACS loading dose: 300–600 mg once. "
            "Reduce efficacy in poor CYP2C19 metabolizers (*2/*2 genotype)."
        ),
    },
    "hydrochlorothiazide": {
        "rxcui": "5487",
        "aliases": ["hctz", "microzide", "hydrodiuril"],
        "max_single_dose_mg": 50.0,
        "max_daily_dose_mg": 100.0,
        "typical_adult_dose_mg": 25.0,
        "routes": ["oral"],
        "notes": (
            "HTN: 25–50 mg/day. Edema: 25–100 mg/day in 1–2 doses. "
            "Monitor serum electrolytes (K+, Na+, Mg2+). Sulfonamide structure."
        ),
    },
    "prednisone": {
        "rxcui": "8638",
        "aliases": ["deltasone", "rayos"],
        "max_single_dose_mg": 80.0,
        "max_daily_dose_mg": 80.0,
        "typical_adult_dose_mg": 10.0,
        "routes": ["oral"],
        "notes": (
            "Short courses: up to 60–80 mg/day. Taper if used >1 week. "
            "Raises blood glucose; monitor in diabetics. Many metabolic adverse effects."
        ),
    },
    "albuterol": {
        "rxcui": "435",
        "aliases": ["salbutamol", "ventolin", "proventil", "proair"],
        "max_single_dose_mg": 4.0,   # oral tablet dose; inhaler doses are in mcg
        "max_daily_dose_mg": 32.0,
        "typical_adult_dose_mg": 2.0,
        "routes": ["oral", "inhaled"],
        "notes": (
            "Inhaler (MDI): 90 mcg/actuation, 2 puffs q4–6h PRN. "
            "Oral tablet: 2–4 mg q6–8h. Note: oral dose in mg; inhaled dose in mcg."
        ),
    },
}

# Build reverse lookup: alias → canonical name
DRUG_ALIASES: dict[str, str] = {}
for _name, _info in DOSE_TABLE.items():
    DRUG_ALIASES[_name] = _name
    for _alias in _info.get("aliases", []):
        DRUG_ALIASES[_alias] = _name

# ---------------------------------------------------------------------------
# Allergen cross-reactivity classes
# Keys: class name; values: list of lowercase drug names in that class.
# ---------------------------------------------------------------------------
ALLERGEN_CLASSES: dict[str, list[str]] = {
    "penicillin": [
        "amoxicillin", "ampicillin", "dicloxacillin", "nafcillin", "oxacillin",
        "penicillin v", "penicillin g", "piperacillin", "ticarcillin",
        "amoxicillin-clavulanate", "ampicillin-sulbactam",
        "piperacillin-tazobactam", "ticarcillin-clavulanate",
    ],
    "cephalosporin": [
        "cephalexin", "cefazolin", "cefuroxime", "ceftriaxone", "cefdinir",
        "cefepime", "ceftazidime", "cefotaxime", "cefprozil", "cefoxitin",
        "cefadroxil", "cefpodoxime", "cefixime", "ceftaroline",
    ],
    "sulfonamide": [
        "sulfamethoxazole", "trimethoprim-sulfamethoxazole", "sulfadiazine",
        "sulfisoxazole", "dapsone", "furosemide", "hydrochlorothiazide",
        "celecoxib", "acetazolamide", "probenecid",
    ],
    "nsaid": [
        "ibuprofen", "naproxen", "aspirin", "diclofenac", "indomethacin",
        "ketorolac", "meloxicam", "celecoxib", "piroxicam", "etodolac",
        "sulindac", "nabumetone",
    ],
    "macrolide": [
        "azithromycin", "clarithromycin", "erythromycin", "fidaxomicin",
        "telithromycin",
    ],
    "fluoroquinolone": [
        "ciprofloxacin", "levofloxacin", "moxifloxacin", "ofloxacin",
        "norfloxacin", "gemifloxacin", "delafloxacin",
    ],
    "statin": [
        "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin",
        "fluvastatin", "lovastatin", "pitavastatin",
    ],
    "ace_inhibitor": [
        "lisinopril", "enalapril", "ramipril", "benazepril", "captopril",
        "fosinopril", "moexipril", "perindopril", "quinapril", "trandolapril",
    ],
    "angiotensin_receptor_blocker": [
        "losartan", "valsartan", "irbesartan", "candesartan", "telmisartan",
        "olmesartan", "azilsartan", "eprosartan",
    ],
    "beta_blocker": [
        "metoprolol", "atenolol", "carvedilol", "bisoprolol", "propranolol",
        "labetalol", "nebivolol", "nadolol", "pindolol", "timolol",
    ],
    "thiazide_diuretic": [
        "hydrochlorothiazide", "chlorthalidone", "metolazone", "indapamide",
        "chlorothiazide", "bendroflumethiazide",
    ],
    "tetracycline": [
        "tetracycline", "doxycycline", "minocycline", "tigecycline",
        "sarecycline", "omadacycline",
    ],
}

# Build drug → classes reverse lookup
DRUG_TO_CLASSES: dict[str, list[str]] = {}
for _class_name, _drugs in ALLERGEN_CLASSES.items():
    for _drug in _drugs:
        DRUG_TO_CLASSES.setdefault(_drug, []).append(_class_name)
