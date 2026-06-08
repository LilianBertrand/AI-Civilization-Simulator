import pandas as pd

TECHS = [
    (8, "Agriculture"), (14, "Writing"), (22, "Metallurgy"), (32, "Navigation"),
    (45, "Administration"), (60, "Banking"), (78, "Gunpowder"), (100, "Industry"),
    (130, "Electricity"), (165, "Computing")
]

class TechnologyEngine:
    def __init__(self):
        self.events = []

    def initialize(self, civilizations):
        for civ in civilizations:
            civ.discovered_techs = []
            civ.innovation = civ.technology * 2

    def update(self, year, civilizations):
        for civ in civilizations:
            focus = 1.45 if civ.personality == "scientific" else 1.0
            wealth_factor = max(0, civ.wealth) / 180000
            stability_factor = max(0, civ.stability) / 150
            civ.technology += 0.006 * focus + wealth_factor + stability_factor * 0.002
            civ.innovation = civ.technology * focus
            for threshold, name in TECHS:
                if civ.technology >= threshold and name not in civ.discovered_techs:
                    civ.discovered_techs.append(name)
                    civ.stability = min(100, civ.stability + 1.5)
                    civ.wealth += threshold * 12
                    self.events.append({"year": year, "civilization": civ.name, "event": f"{civ.name} discovered {name}, reshaping its economy and institutions."})

    def dataframe(self, civilizations):
        rows = []
        for civ in civilizations:
            rows.append({
                "Civilization": civ.name,
                "Technology Level": round(civ.technology, 2),
                "Innovation": round(getattr(civ, "innovation", 0), 2),
                "Discovered Technologies": ", ".join(getattr(civ, "discovered_techs", [])) or "None yet",
                "Tech Count": len(getattr(civ, "discovered_techs", [])),
            })
        return pd.DataFrame(rows).sort_values("Technology Level", ascending=False)
