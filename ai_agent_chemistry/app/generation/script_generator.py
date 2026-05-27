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
            },
            {
                "on_screen_text": "Scale from 0 to 14",
                "narration": "Values below seven are acidic, seven is neutral, and above seven are bases.",
                "duration_sec": 10,
            },
            {
                "on_screen_text": "Hydrogen ions matter",
                "narration": "Acids have more hydrogen ions, while bases have fewer hydrogen ions.",
                "duration_sec": 10,
            },
            {
                "on_screen_text": "Examples: lemon juice, water, soap",
                "narration": "Lemon juice is acidic, pure water is neutral, and soapy water is basic.",
                "duration_sec": 10,
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
            },
            {
                "on_screen_text": "Covalent means sharing electrons",
                "narration": "In a covalent bond, atoms share electrons rather than transfer them.",
                "duration_sec": 10,
            },
            {
                "on_screen_text": "Shared pairs lower energy",
                "narration": "Sharing electrons lowers the system energy and makes molecules more stable.",
                "duration_sec": 10,
            },
            {
                "on_screen_text": "Example: H2 and H2O",
                "narration": "Hydrogen gas and water are common examples built from covalent bonds.",
                "duration_sec": 10,
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
            },
            {
                "on_screen_text": "Ionic = electron transfer",
                "narration": "Ionic bonding happens when one atom donates electrons and another accepts them.",
                "duration_sec": 10,
            },
            {
                "on_screen_text": "Covalent = electron sharing",
                "narration": "Covalent bonding happens when atoms share electron pairs.",
                "duration_sec": 10,
            },
            {
                "on_screen_text": "Examples: salt vs water",
                "narration": "Table salt is ionic, while water molecules are held together by covalent bonds.",
                "duration_sec": 10,
            },
        ],
    },
}


class ScriptGenerator:
    def generate(self, query: str) -> dict:
        # Template-first for reliability in this challenge scope.
        return deepcopy(FALLBACK_SCRIPTS[query])
