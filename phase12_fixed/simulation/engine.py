import pandas as pd
from economy.economy_engine import EconomyEngine, RESOURCE_COLUMNS
from markets.market_engine import MarketEngine
from diplomacy.diplomacy_engine import DiplomacyEngine
from religion.religion_engine import ReligionEngine
from technology.technology_engine import TechnologyEngine
from politics.leader_engine import LeaderEngine
from crises.crisis_engine import CrisisEngine
from extensions.future_engine import FutureEngine

class SimulationEngine:
    def __init__(self, world_map, civilizations):
        self.world_map = world_map
        self.civilizations = civilizations
        self.economy = EconomyEngine()
        self.market = MarketEngine()
        self.diplomacy = DiplomacyEngine()
        self.religion = ReligionEngine()
        self.technology = TechnologyEngine()
        self.leaders = LeaderEngine()
        self.crises = CrisisEngine()
        self.future = FutureEngine()
        self.diplomacy.initialize(civilizations)
        self.religion.initialize(civilizations)
        self.technology.initialize(civilizations)
        self.leaders.initialize(civilizations)
        self.future.initialize(civilizations)
        self.year = 0
        self.history = []
        self.events = []

    def step(self):
        self.year += 1

        # Diplomacy is evaluated first so wars influence yearly demand.
        self.diplomacy.update(self.year, self.civilizations, self.world_map, self.market.prices)
        self.events.extend(self.diplomacy.events)
        self.diplomacy.events = []

        for civ in self.civilizations:
            self.economy.update_civilization(civ, self.world_map, self.market.prices)
            self._expand(civ)

        self.market.update(self.year, self.civilizations)
        self.events.extend(self.market.events)
        self.market.events = []

        self.technology.update(self.year, self.civilizations)
        self.events.extend(self.technology.events)
        self.technology.events = []
        self.religion.update(self.year, self.civilizations)
        self.events.extend(self.religion.events)
        self.religion.events = []
        self.leaders.update(self.year, self.civilizations)
        self.events.extend(self.leaders.events)
        self.leaders.events = []
        self.crises.update(self.year, self.civilizations, self.market.prices)
        self.events.extend(self.crises.events)
        self.crises.events = []

        active_wars = sum(1 for status in self.diplomacy.statuses.values() if status == "War")
        self.future.update(self.year, self.civilizations, self.market.prices, active_wars=active_wars)
        self.events.extend(self.future.events)
        self.future.events = []

        self._record_economic_events()
        self._record_geopolitical_events()
        self._record_civilization_events()
        self._record_history()

    def run(self, years: int):
        for _ in range(years):
            self.step()

    def _expand(self, civ):
        frontier = []
        for x, y in list(civ.territory):
            tile = self.world_map.get_tile(x, y)
            if tile is None:
                continue
            for neighbor in self.world_map.neighbors(tile):
                if neighbor.is_habitable and neighbor.owner_id is None:
                    frontier.append(neighbor)

        if not frontier:
            return

        expansion_capacity = 1
        if civ.personality == "expansionist":
            expansion_capacity = 2
        if civ.wealth > 1000 and civ.population > 2000:
            expansion_capacity += 1
        if len(civ.territory) > 90:
            expansion_capacity = max(1, expansion_capacity - 1)
        if getattr(civ, "at_war", False):
            expansion_capacity = max(1, expansion_capacity - 1)

        frontier = sorted(frontier, key=lambda t: t.total_resources, reverse=True)
        for target in frontier[:expansion_capacity]:
            expansion_cost = 35 + len(civ.territory) * 1.15 + max(0, len(civ.territory) - 80) * 2.8
            if len(civ.territory) > 120:
                civ.stability = max(20, civ.stability - 0.08)
            if civ.wealth >= expansion_cost and civ.stability > 25:
                civ.wealth -= expansion_cost
                target.owner_id = civ.id
                civ.territory.add((target.x, target.y))
                if len(civ.territory) % 18 == 0:
                    target.city_id = civ.id
                    self.events.append({
                        "year": self.year,
                        "civilization": civ.name,
                        "event": f"{civ.name} founded a new city near ({target.x}, {target.y})."
                    })

    def _record_economic_events(self):
        if self.year % 25 != 0:
            return
        strongest_exporter = max(self.civilizations, key=lambda c: c.trade_balance)
        weakest_importer = min(self.civilizations, key=lambda c: c.trade_balance)
        self.events.append({
            "year": self.year,
            "civilization": strongest_exporter.name,
            "event": f"{strongest_exporter.name} became a major net exporter with a trade surplus of {strongest_exporter.trade_balance:,.0f}."
        })
        self.events.append({
            "year": self.year,
            "civilization": weakest_importer.name,
            "event": f"{weakest_importer.name} recorded a trade deficit of {abs(weakest_importer.trade_balance):,.0f}, increasing economic pressure."
        })

    def _record_geopolitical_events(self):
        if self.year % 50 != 0:
            return
        active_wars = sum(1 for status in self.diplomacy.statuses.values() if status == "War")
        alliances = sum(1 for status in self.diplomacy.statuses.values() if status == "Alliance")
        rivalries = sum(1 for status in self.diplomacy.statuses.values() if status == "Rivalry")
        self.events.append({
            "year": self.year,
            "civilization": "Geopolitics",
            "event": f"The world order recorded {active_wars} active wars, {alliances} alliances and {rivalries} strategic rivalries."
        })


    def _record_civilization_events(self):
        if self.year % 40 != 0:
            return
        most_advanced = max(self.civilizations, key=lambda c: c.technology)
        least_stable = min(self.civilizations, key=lambda c: c.stability)
        most_faithful = max(self.civilizations, key=lambda c: getattr(c, "faith", 0))
        self.events.append({
            "year": self.year,
            "civilization": most_advanced.name,
            "event": f"{most_advanced.name} became the technological leader of the age with a technology level of {most_advanced.technology:.1f}."
        })
        self.events.append({
            "year": self.year,
            "civilization": least_stable.name,
            "event": f"Internal instability weakened {least_stable.name}, reducing confidence in its institutions."
        })
        self.events.append({
            "year": self.year,
            "civilization": most_faithful.name,
            "event": f"{most_faithful.religion} gained major influence across {most_faithful.name}."
        })

    def _record_history(self):
        world_gdp = sum(c.gdp for c in self.civilizations)
        world_population = sum(c.population for c in self.civilizations)
        world_military = sum(c.military for c in self.civilizations)
        avg_technology = sum(c.technology for c in self.civilizations) / len(self.civilizations)
        avg_stability = sum(c.stability for c in self.civilizations) / len(self.civilizations)
        avg_faith = sum(getattr(c, "faith", 0) for c in self.civilizations) / len(self.civilizations)
        active_crises = len(getattr(self.crises, "active_crises", []))
        weather_df = self.future.weather_dataframe()
        phase_df = self.future.phase_dataframe()
        latest_weather = weather_df.iloc[-1].to_dict() if not weather_df.empty else {}
        latest_phase = phase_df.iloc[-1].to_dict() if not phase_df.empty else {}
        avg_inflation = sum(getattr(c, "inflation", 0) for c in self.civilizations) / len(self.civilizations)
        avg_policy_rate = sum(getattr(c, "central_bank_rate", 0) for c in self.civilizations) / len(self.civilizations)
        total_territory = sum(len(c.territory) for c in self.civilizations)
        total_trade_balance = sum(c.trade_balance for c in self.civilizations)
        latest_market = self.market.history[-1] if self.market.history else {}
        active_wars = sum(1 for status in self.diplomacy.statuses.values() if status == "War")
        alliances = sum(1 for status in self.diplomacy.statuses.values() if status == "Alliance")
        rivalries = sum(1 for status in self.diplomacy.statuses.values() if status == "Rivalry")
        war_risk_index = min(100, active_wars * 18 + rivalries * 4 + max(0, 100 - avg_stability) * 0.8)
        self.history.append({
            "year": self.year,
            "world_gdp": world_gdp,
            "world_population": world_population,
            "world_military": world_military,
            "avg_technology": avg_technology,
            "avg_stability": avg_stability,
            "controlled_tiles": total_territory,
            "commodity_index": latest_market.get("commodity_index", 100),
            "total_trade_balance": total_trade_balance,
            "active_wars": active_wars,
            "alliances": alliances,
            "rivalries": rivalries,
            "war_risk_index": war_risk_index,
            "avg_faith": avg_faith,
            "active_crises": active_crises,
            "weather_stress_index": latest_weather.get("Weather Stress Index", 0),
            "industrialization_index": latest_phase.get("Industrialization Index", 0),
            "modern_world_index": latest_phase.get("Modern World Index", 0),
            "space_race_index": latest_phase.get("Space Race Index", 0),
            "avg_inflation": avg_inflation,
            "avg_policy_rate": avg_policy_rate,
        })

    def civilization_dataframe(self):
        return pd.DataFrame([
            {
                "Civilization": c.name,
                "Personality": c.personality,
                "Population": round(c.population),
                "GDP": round(c.gdp, 2),
                "Wealth": round(c.wealth, 2),
                "Military": round(c.military, 2),
                "Technology": round(c.technology, 2),
                "Stability": round(c.stability, 2),
                "Territory": len(c.territory),
                "Trade Balance": round(c.trade_balance, 2),
                "Main Export": self._main_resource(c.exports),
                "Main Import": self._main_resource(c.imports),
                "Allies": len(getattr(c, "allies", [])),
                "Rivals": len(getattr(c, "rivals", [])),
                "At War": "Yes" if getattr(c, "at_war", False) else "No",
                "Religion": getattr(c, "religion", "None"),
                "Faith": round(getattr(c, "faith", 0), 2),
                "Leader": f"{getattr(c, 'leader_title', 'Leader')} {getattr(c, 'leader_name', 'Unknown')}",
                "Crisis Risk": "High" if c.stability < 45 else ("Medium" if c.stability < 70 else "Low"),
                "Power Score": round(c.power_score, 2),
                "Climate": getattr(c, "climate", "Unknown"),
                "Drought Risk": round(getattr(c, "drought_risk", 0), 2),
                "Inflation": round(getattr(c, "inflation", 0), 2),
                "Policy Rate": round(getattr(c, "central_bank_rate", 0), 2),
                "Stock Index": round(getattr(c, "stock_index", 100), 2),
                "Industrialization": round(getattr(c, "industrialization", 0), 2),
                "Modernization": round(getattr(c, "modernization", 0), 2),
                "Space Progress": round(getattr(c, "space_progress", 0), 2),
            }
            for c in self.civilizations
        ]).sort_values("Power Score", ascending=False)

    def trade_dataframe(self):
        rows = []
        for civ in self.civilizations:
            for resource in RESOURCE_COLUMNS:
                rows.append({
                    "Civilization": civ.name,
                    "Resource": resource.title(),
                    "Production": round(civ.production.get(resource, 0), 2),
                    "Consumption": round(civ.demand.get(resource, 0), 2),
                    "Exports": round(civ.exports.get(resource, 0), 2),
                    "Imports": round(civ.imports.get(resource, 0), 2),
                })
        return pd.DataFrame(rows)

    def market_dataframe(self):
        return self.market.market_dataframe()

    def market_history_dataframe(self):
        return self.market.history_dataframe()

    def diplomacy_dataframe(self):
        return self.diplomacy.dataframe(self.civilizations)

    def war_dataframe(self):
        return self.diplomacy.war_dataframe(self.civilizations)

    def technology_dataframe(self):
        return self.technology.dataframe(self.civilizations)

    def religion_dataframe(self):
        import pandas as pd
        return pd.DataFrame([{
            "Civilization": c.name,
            "Religion": getattr(c, "religion", "None"),
            "Faith Influence": round(getattr(c, "faith", 0), 2),
            "Religious Unity": round(getattr(c, "religious_unity", 0), 2),
            "Personality": c.personality,
            "Population": round(c.population),
        } for c in self.civilizations]).sort_values("Faith Influence", ascending=False)

    def leader_dataframe(self):
        return self.leaders.dataframe(self.civilizations)

    def crisis_dataframe(self):
        return self.crises.dataframe()

    def weather_dataframe(self):
        return self.future.weather_dataframe()

    def disaster_dataframe(self):
        return self.future.disaster_dataframe()

    def company_dataframe(self):
        return self.future.company_dataframe()

    def financial_dataframe(self):
        return self.future.financial_dataframe()

    def central_bank_dataframe(self):
        return self.future.central_bank_dataframe()

    def phase_dataframe(self):
        return self.future.phase_dataframe()

    def history_dataframe(self):
        return pd.DataFrame(self.history)

    def events_dataframe(self):
        return pd.DataFrame(self.events)

    @staticmethod
    def _main_resource(values: dict) -> str:
        if not values:
            return "None"
        resource, amount = max(values.items(), key=lambda item: item[1])
        return resource.title() if amount > 0 else "None"
