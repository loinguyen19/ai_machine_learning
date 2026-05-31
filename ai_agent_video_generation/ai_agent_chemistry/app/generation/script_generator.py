from __future__ import annotations

from copy import deepcopy


FALLBACK_SCRIPTS = {
    "How does the pH scale work?": {
        "title": "How the pH Scale Works",
        "scenes": [
            {
                "on_screen_text": "pH measures acidity and basicity",
                "narration": "The pH scale tells us how acidic or basic a solution is.",
                "duration_sec": 8,
                "visual": "ph_intro",
            },
            {
                "on_screen_text": "Scale from 0 to 14",
                "narration": "Values below seven are acidic, seven is neutral, and above seven are bases.",
                "duration_sec": 10,
                "visual": "ph_scale",
            },
            {
                "on_screen_text": "Hydrogen ions matter",
                "narration": "Acids have more hydrogen ions, while bases have fewer hydrogen ions.",
                "duration_sec": 10,
                "visual": "ph_ions",
            },
            {
                "on_screen_text": "Examples: lemon juice, water, soap",
                "narration": "Lemon juice is acidic, pure water is neutral, and soapy water is basic.",
                "duration_sec": 10,
                "visual": "ph_examples",
            },
        ],
    },
    "Why do atoms form covalent bonds?": {
        "title": "Why Atoms Form Covalent Bonds",
        "scenes": [
            {
                "on_screen_text": "Atoms seek stable outer shells",
                "narration": "Atoms form covalent bonds to reach stable electron arrangements.",
                "duration_sec": 8,
                "visual": "covalent_shells",
            },
            {
                "on_screen_text": "Covalent means sharing electrons",
                "narration": "In a covalent bond, atoms share electrons rather than transfer them.",
                "duration_sec": 10,
                "visual": "covalent_sharing",
            },
            {
                "on_screen_text": "Shared pairs lower energy",
                "narration": "Sharing electrons lowers the system energy and makes molecules more stable.",
                "duration_sec": 10,
                "visual": "covalent_energy",
            },
            {
                "on_screen_text": "Example: H2 and H2O",
                "narration": "Hydrogen gas and water are common examples built from covalent bonds.",
                "duration_sec": 10,
                "visual": "covalent_examples",
            },
        ],
    },
    "What is the difference between ionic and covalent bonding?": {
        "title": "Ionic vs Covalent Bonding",
        "scenes": [
            {
                "on_screen_text": "Two ways atoms bond",
                "narration": "Atoms can bond by transferring electrons or by sharing electrons.",
                "duration_sec": 8,
                "visual": "bonding_overview",
            },
            {
                "on_screen_text": "Ionic = electron transfer",
                "narration": "Ionic bonding happens when one atom donates electrons and another accepts them.",
                "duration_sec": 10,
                "visual": "ionic_transfer",
            },
            {
                "on_screen_text": "Covalent = electron sharing",
                "narration": "Covalent bonding happens when atoms share electron pairs.",
                "duration_sec": 10,
                "visual": "covalent_diagram",
            },
            {
                "on_screen_text": "Examples: salt vs water",
                "narration": "Table salt is ionic, while water molecules are held together by covalent bonds.",
                "duration_sec": 10,
                "visual": "bonding_examples",
            },
        ],
    },
}


class ScriptGenerator:
    """Template-first script generation for reliability and zero LLM cost.

    Set USE_LLM_SCRIPT=1 to swap in an LLM provider later; templates remain
    the fallback when LLM output fails validation.
    """

    def generate(self, query: str) -> dict:
        if query not in FALLBACK_SCRIPTS:
            raise KeyError(f"No script template for query: {query}")
        return deepcopy(FALLBACK_SCRIPTS[query])
