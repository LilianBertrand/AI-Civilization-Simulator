import random
import pandas as pd

class CrisisEngine:
    def __init__(self, seed=42):
        self.rng = random.Random(seed + 202)
        self.events = []
        self.active_crises = []

    def update(self, year, civilizations, market_prices):
        self.active_crises = []
        for civ in civilizations:
            risk = 0.015
            if civ.stability < 45: risk += 0.04
            if civ.trade_balance < -5000: risk += 0.025
            if getattr(civ, "at_war", False): risk += 0.025
            if civ.imports.get("food", 0) > civ.production.get("food", 1) * 0.25: risk += 0.02
            if self.rng.random() < risk:
                crisis = self.rng.choice(["Famine", "Debt Crisis", "Noble Revolt", "Succession Crisis", "Trade Shock"])
                severity = self.rng.randint(20, 90)
                self._apply(civ, crisis, severity)
                self.active_crises.append({"Year": year, "Civilization": civ.name, "Crisis": crisis, "Severity": severity})
                self.events.append({"year": year, "civilization": civ.name, "event": f"{civ.name} suffered a {crisis.lower()} with severity {severity}/100."})

    def _apply(self, civ, crisis, severity):
        impact = severity / 100
        civ.stability = max(0, civ.stability - 8 * impact)
        if crisis == "Famine":
            civ.population *= 1 - 0.035 * impact
            civ.food_stock = max(0, civ.food_stock * (1 - 0.3 * impact))
        elif crisis == "Debt Crisis":
            civ.wealth *= 1 - 0.08 * impact
        elif crisis == "Noble Revolt":
            civ.military *= 1 - 0.04 * impact
        elif crisis == "Succession Crisis":
            civ.leader_legitimacy = max(0, getattr(civ, "leader_legitimacy", 50) - 20 * impact)
        elif crisis == "Trade Shock":
            civ.wealth *= 1 - 0.05 * impact

    def dataframe(self):
        return pd.DataFrame(self.active_crises)
