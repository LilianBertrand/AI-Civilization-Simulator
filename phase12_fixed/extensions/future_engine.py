import random
import pandas as pd

SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
CLIMATES = ["Temperate", "Dry", "Wet", "Cold"]
SECTORS = ["Agriculture", "Mining", "Industry", "Trade", "Finance", "Energy", "Aerospace"]

class FutureEngine:
    """Phase 7 extension layer: climate, disasters, firms, central banks, markets,
    industrialization, modernity and space race signals.

    The module is intentionally compact: it adds strategic macro variables without
    turning the project into a full game engine.
    """
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.events = []
        self.weather_history = []
        self.disasters = []
        self.companies = []
        self.financial_history = []
        self.central_bank_history = []
        self.phase_history = []

    def initialize(self, civilizations):
        for civ in civilizations:
            civ.climate = self.rng.choice(CLIMATES)
            civ.season = "Spring"
            civ.drought_risk = self.rng.uniform(5, 18)
            civ.weather_shock = 0.0
            civ.central_bank_rate = self.rng.uniform(1.0, 4.0)
            civ.inflation = self.rng.uniform(1.0, 4.5)
            civ.debt_to_gdp = self.rng.uniform(20, 65)
            civ.stock_index = 100.0 + self.rng.uniform(-8, 8)
            civ.bond_yield = civ.central_bank_rate + self.rng.uniform(0.5, 2.0)
            civ.industrialization = 0.0
            civ.modernization = 0.0
            civ.space_progress = 0.0
            civ.companies = []
            # Seed one private company per civilization.
            sector = self.rng.choice(SECTORS[:4])
            name = f"{civ.name.split()[0]} {sector} Company"
            firm = {
                "Civilization": civ.name,
                "Company": name,
                "Sector": sector,
                "Market Cap": round(self.rng.uniform(80, 260), 2),
                "Revenue": round(self.rng.uniform(35, 120), 2),
                "Strategic Importance": round(self.rng.uniform(25, 70), 2),
            }
            civ.companies.append(firm)
            self.companies.append(firm)

    def update(self, year, civilizations, market_prices, active_wars=0):
        season = SEASONS[(year - 1) % 4]
        global_weather_stress = 0.0
        disaster_pressure = 0

        for civ in civilizations:
            civ.season = season
            climate_base = {"Temperate": 8, "Dry": 18, "Wet": 10, "Cold": 12}.get(civ.climate, 10)
            seasonal_multiplier = {"Spring": 0.85, "Summer": 1.25, "Autumn": 0.75, "Winter": 1.05}[season]
            drought_risk = min(100, climate_base * seasonal_multiplier + max(0, market_prices.get("food", 1) - 1) * 8 + self.rng.uniform(-4, 6))
            civ.drought_risk = max(0, drought_risk)
            civ.weather_shock = 0.0

            # Drought and seasonal shocks influence food, stability and GDP.
            if civ.drought_risk > 25 and self.rng.random() < min(0.22, civ.drought_risk / 420):
                severity = self.rng.uniform(3, 10)
                civ.population *= (1 - severity / 2500)
                civ.stability = max(5, civ.stability - severity * 0.9)
                civ.wealth = max(0, civ.wealth - severity * 6)
                civ.weather_shock = severity
                self.events.append({"year": year, "civilization": civ.name, "event": f"A severe drought hit {civ.name}, weakening food security and stability."})
            global_weather_stress += civ.drought_risk

            # Natural disasters.
            disaster_probability = 0.006 + max(0, 65 - civ.stability) / 10000
            if self.rng.random() < disaster_probability:
                disaster_type = self.rng.choice(["earthquake", "flood", "volcanic eruption", "pandemic wave", "major storm"])
                severity = self.rng.uniform(8, 28)
                civ.population *= (1 - severity / 5000)
                civ.wealth = max(0, civ.wealth - severity * 10)
                civ.stability = max(5, civ.stability - severity * 0.65)
                disaster_pressure += 1
                record = {"Year": year, "Civilization": civ.name, "Disaster": disaster_type.title(), "Severity": round(severity, 1), "Impact": "Population, wealth and stability shock"}
                self.disasters.append(record)
                self.events.append({"year": year, "civilization": civ.name, "event": f"A {disaster_type} struck {civ.name}, creating a major humanitarian and economic shock."})

            # Industrial revolution and modern transition.
            if civ.technology > 7:
                civ.industrialization = min(100, civ.industrialization + 0.10 + civ.technology / 250 + self.rng.uniform(0, 0.08))
            if civ.technology > 13 and civ.industrialization > 35:
                civ.modernization = min(100, civ.modernization + 0.08 + civ.industrialization / 900 + self.rng.uniform(0, 0.06))
            if civ.technology > 22 and civ.modernization > 55:
                civ.space_progress = min(100, civ.space_progress + 0.04 + civ.technology / 650 + self.rng.uniform(0, 0.05))

            # Private companies scale with wealth, technology and industrialization.
            if year % 40 == 0 and (civ.industrialization > 5 or civ.technology > 5):
                sector_pool = SECTORS[:]
                if civ.industrialization < 15 and "Aerospace" in sector_pool:
                    sector_pool.remove("Aerospace")
                sector = self.rng.choice(sector_pool)
                firm = {
                    "Civilization": civ.name,
                    "Company": f"{civ.name.split()[0]} {sector} Trust",
                    "Sector": sector,
                    "Market Cap": round(120 + civ.wealth * 0.08 + civ.technology * 35 + self.rng.uniform(0, 160), 2),
                    "Revenue": round(45 + civ.yearly_wealth * 0.12 + self.rng.uniform(0, 90), 2),
                    "Strategic Importance": round(min(100, 20 + civ.industrialization * 0.6 + civ.technology * 1.5 + self.rng.uniform(0, 20)), 2),
                }
                civ.companies.append(firm)
                self.companies.append(firm)
                self.events.append({"year": year, "civilization": civ.name, "event": f"{firm['Company']} emerged as a strategic private company in the {sector.lower()} sector."})

            # Central banks and simulated financial markets.
            inflation_pressure = market_prices.get("food", 1) * 0.18 + market_prices.get("iron", 1) * 0.08 + active_wars * 0.20
            civ.inflation = max(-3, min(35, civ.inflation * 0.86 + inflation_pressure + self.rng.uniform(-0.35, 0.55)))
            target_rate = 1.5 + max(0, civ.inflation - 2) * 0.45 + active_wars * 0.10
            civ.central_bank_rate = max(0, min(25, civ.central_bank_rate * 0.88 + target_rate * 0.12))
            civ.bond_yield = max(0.1, civ.central_bank_rate + civ.debt_to_gdp / 120 + max(0, 70 - civ.stability) / 35)
            equity_return = (civ.gdp / max(civ.population, 1)) / 800 + civ.technology / 500 + civ.stability / 4000 - civ.central_bank_rate / 900 - active_wars / 250 + self.rng.uniform(-0.012, 0.018)
            civ.stock_index = max(10, civ.stock_index * (1 + equity_return))

            self.central_bank_history.append({
                "year": year, "Civilization": civ.name, "Inflation": round(civ.inflation, 2), "Policy Rate": round(civ.central_bank_rate, 2), "Debt/GDP": round(civ.debt_to_gdp, 2), "Bond Yield": round(civ.bond_yield, 2)
            })
            self.financial_history.append({
                "year": year, "Civilization": civ.name, "Stock Index": round(civ.stock_index, 2), "Bond Yield": round(civ.bond_yield, 2), "Policy Rate": round(civ.central_bank_rate, 2), "Inflation": round(civ.inflation, 2)
            })

        self.weather_history.append({
            "year": year,
            "Season": season,
            "Weather Stress Index": round(global_weather_stress / max(len(civilizations), 1), 2),
            "Disasters This Year": disaster_pressure,
        })

        avg_industrial = sum(c.industrialization for c in civilizations) / len(civilizations)
        avg_modern = sum(c.modernization for c in civilizations) / len(civilizations)
        avg_space = sum(c.space_progress for c in civilizations) / len(civilizations)
        self.phase_history.append({
            "year": year,
            "Industrialization Index": round(avg_industrial, 2),
            "Modern World Index": round(avg_modern, 2),
            "Space Race Index": round(avg_space, 2),
        })

    def weather_dataframe(self):
        return pd.DataFrame(self.weather_history)

    def disaster_dataframe(self):
        return pd.DataFrame(self.disasters)

    def company_dataframe(self):
        return pd.DataFrame(self.companies).sort_values("Market Cap", ascending=False) if self.companies else pd.DataFrame()

    def financial_dataframe(self):
        return pd.DataFrame(self.financial_history)

    def central_bank_dataframe(self):
        return pd.DataFrame(self.central_bank_history)

    def phase_dataframe(self):
        return pd.DataFrame(self.phase_history)
