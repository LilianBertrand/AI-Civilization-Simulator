import random
import pandas as pd

FIRST = ["Aurel", "Selene", "Kaeron", "Mira", "Thalos", "Nyra", "Eldric", "Varon", "Zara", "Orian"]
TITLES = ["High Chancellor", "Queen", "Emperor", "Strategos", "Archon", "First Speaker", "Warlord", "Sage-King"]
TRAITS = ["ambitious", "pragmatic", "zealous", "diplomatic", "ruthless", "visionary", "cautious", "reformist"]

class LeaderEngine:
    def __init__(self, seed=42):
        self.rng = random.Random(seed + 99)
        self.events = []

    def initialize(self, civilizations):
        for civ in civilizations:
            civ.leader_name = self.rng.choice(FIRST) + " " + self.rng.choice(["I", "II", "III", "the Bold", "the Wise", "of the River"])
            civ.leader_title = self.rng.choice(TITLES)
            civ.leader_trait = self.rng.choice(TRAITS)
            civ.leader_age = self.rng.randint(28, 62)
            civ.leader_legitimacy = self.rng.randint(45, 90)

    def update(self, year, civilizations):
        for civ in civilizations:
            civ.leader_age += 1
            if civ.leader_trait == "diplomatic":
                civ.stability = min(100, civ.stability + 0.04)
            elif civ.leader_trait == "ruthless":
                civ.military *= 1.001
                civ.stability = max(0, civ.stability - 0.025)
            elif civ.leader_trait == "visionary":
                civ.technology += 0.01
            elif civ.leader_trait == "zealous":
                civ.faith = min(100, getattr(civ, "faith", 20) + 0.08)

            death_chance = max(0.005, (civ.leader_age - 60) * 0.006)
            if self.rng.random() < death_chance:
                old = f"{civ.leader_title} {civ.leader_name}"
                self._new_leader(civ)
                civ.stability = max(0, civ.stability - self.rng.uniform(1, 6))
                self.events.append({"year": year, "civilization": civ.name, "event": f"{old} died. {civ.leader_title} {civ.leader_name}, a {civ.leader_trait} ruler, rose to power."})

    def _new_leader(self, civ):
        civ.leader_name = self.rng.choice(FIRST) + " " + self.rng.choice(["I", "II", "III", "the Younger", "the Iron", "of Dawn"])
        civ.leader_title = self.rng.choice(TITLES)
        civ.leader_trait = self.rng.choice(TRAITS)
        civ.leader_age = self.rng.randint(24, 48)
        civ.leader_legitimacy = self.rng.randint(35, 85)

    def dataframe(self, civilizations):
        return pd.DataFrame([{
            "Civilization": c.name,
            "Leader": f"{c.leader_title} {c.leader_name}",
            "Trait": c.leader_trait,
            "Age": c.leader_age,
            "Legitimacy": c.leader_legitimacy,
            "Stability": round(c.stability, 2),
        } for c in civilizations])
