import random
import pandas as pd

RELIGION_NAMES = [
    "Solar Covenant", "Order of the Deep Flame", "Celestial Path", "Temple of the First River",
    "Ashen Doctrine", "Harmony of the Five Winds", "Cult of the Golden Dawn", "Silent Star Faith"
]

class ReligionEngine:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.events = []

    def initialize(self, civilizations):
        names = RELIGION_NAMES.copy()
        self.rng.shuffle(names)
        for i, civ in enumerate(civilizations):
            civ.religion = names[i % len(names)]
            civ.faith = 20 + self.rng.random() * 30
            civ.religious_unity = 55 + self.rng.random() * 35

    def update(self, year, civilizations):
        if year % 7 != 0:
            return
        for civ in civilizations:
            personality_bonus = 1.5 if civ.personality == "religious" else 0.4
            growth = personality_bonus + civ.stability * 0.008 + civ.population / 250000
            civ.faith = min(100, getattr(civ, "faith", 20) + growth)
            civ.religious_unity = min(100, getattr(civ, "religious_unity", 60) + growth * 0.22)
            if civ.faith > 75 and year % 35 == 0:
                self.events.append({"year": year, "civilization": civ.name, "event": f"{civ.name} entered a religious golden age under the influence of {civ.religion}."})
