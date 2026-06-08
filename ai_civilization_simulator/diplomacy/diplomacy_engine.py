from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, Tuple, List

import pandas as pd

RESOURCE_COLUMNS = ["food", "wood", "stone", "iron", "gold"]


def _pair(a: int, b: int) -> Tuple[int, int]:
    return tuple(sorted((a, b)))


@dataclass
class DiplomacyEngine:
    """Relationship, alliances, rivalries, treaties and resource-driven wars."""

    relations: Dict[Tuple[int, int], float] = field(default_factory=dict)
    statuses: Dict[Tuple[int, int], str] = field(default_factory=dict)
    active_wars: Dict[Tuple[int, int], dict] = field(default_factory=dict)
    treaties: Dict[Tuple[int, int], int] = field(default_factory=dict)
    events: List[dict] = field(default_factory=list)

    def initialize(self, civilizations: list, seed: int = 0) -> None:
        if self.relations:
            return
        for civ_a, civ_b in combinations(civilizations, 2):
            base = 0.0
            if civ_a.personality == civ_b.personality:
                base += 8
            if "merchant" in (civ_a.personality, civ_b.personality):
                base += 5
            if "militarist" in (civ_a.personality, civ_b.personality):
                base -= 7
            key = _pair(civ_a.id, civ_b.id)
            self.relations[key] = base
            self.statuses[key] = "Neutral"

    def update(self, year: int, civilizations: list, world_map, market_prices: dict) -> None:
        civ_by_id = {c.id: c for c in civilizations}
        self._clear_civilization_diplomacy(civilizations)

        for civ_a, civ_b in combinations(civilizations, 2):
            key = _pair(civ_a.id, civ_b.id)
            relation = self.relations.get(key, 0.0)
            relation += self._trade_compatibility(civ_a, civ_b) * 0.018
            relation -= self._resource_competition(civ_a, civ_b, market_prices) * 0.028
            relation -= self._border_pressure(civ_a, civ_b, world_map) * 0.16
            relation -= self._power_fear(civ_a, civ_b) * 0.004

            if civ_a.personality == "merchant" or civ_b.personality == "merchant":
                relation += 0.05
            if civ_a.personality == "militarist" or civ_b.personality == "militarist":
                relation -= 0.08
            if civ_a.personality == "religious" and civ_b.personality == "religious":
                relation -= 0.03

            # Treaties slowly improve relations while they last.
            if self.treaties.get(key, 0) > 0:
                relation += 0.20
                self.treaties[key] -= 1

            self.relations[key] = max(-100.0, min(100.0, relation))

        self._resolve_existing_wars(year, civilizations, world_map)
        self._open_or_close_relations(year, civilizations, market_prices)
        self._write_civilization_diplomacy(civilizations)

    def dataframe(self, civilizations: list) -> pd.DataFrame:
        civ_by_id = {c.id: c for c in civilizations}
        rows = []
        for key, relation in self.relations.items():
            a, b = key
            rows.append({
                "Civilization A": civ_by_id[a].name,
                "Civilization B": civ_by_id[b].name,
                "Relation Score": round(relation, 2),
                "Status": self.statuses.get(key, "Neutral"),
                "Treaty Years Left": self.treaties.get(key, 0),
            })
        return pd.DataFrame(rows).sort_values("Relation Score")

    def war_dataframe(self, civilizations: list) -> pd.DataFrame:
        civ_by_id = {c.id: c for c in civilizations}
        rows = []
        for key, war in self.active_wars.items():
            a, b = key
            rows.append({
                "Side A": civ_by_id[a].name,
                "Side B": civ_by_id[b].name,
                "Cause": war.get("cause", "Resource rivalry"),
                "Started": war.get("started", 0),
                "Duration": war.get("duration", 0),
                "Intensity": round(war.get("intensity", 0), 2),
            })
        return pd.DataFrame(rows)

    def _clear_civilization_diplomacy(self, civilizations: list) -> None:
        for civ in civilizations:
            civ.allies = set()
            civ.rivals = set()
            civ.enemies = set()
            civ.at_war = False
            civ.war_pressure = 0.0

    def _write_civilization_diplomacy(self, civilizations: list) -> None:
        civ_by_id = {c.id: c for c in civilizations}
        for key, status in self.statuses.items():
            a, b = key
            if status == "Alliance":
                civ_by_id[a].allies.add(b)
                civ_by_id[b].allies.add(a)
            elif status == "Rivalry":
                civ_by_id[a].rivals.add(b)
                civ_by_id[b].rivals.add(a)
            elif status == "War":
                civ_by_id[a].enemies.add(b)
                civ_by_id[b].enemies.add(a)
                civ_by_id[a].at_war = True
                civ_by_id[b].at_war = True
                intensity = self.active_wars.get(key, {}).get("intensity", 1.0)
                civ_by_id[a].war_pressure += intensity
                civ_by_id[b].war_pressure += intensity

    def _open_or_close_relations(self, year: int, civilizations: list, market_prices: dict) -> None:
        civ_by_id = {c.id: c for c in civilizations}
        for civ_a, civ_b in combinations(civilizations, 2):
            key = _pair(civ_a.id, civ_b.id)
            relation = self.relations[key]
            status = self.statuses.get(key, "Neutral")

            scarcity = self._resource_competition(civ_a, civ_b, market_prices)
            military_gap = abs(civ_a.military - civ_b.military) / max(civ_a.military + civ_b.military, 1)

            border_pressure = self._border_pressure(civ_a, civ_b, None) if False else 0
            conflict_pressure = scarcity + abs(relation) * 0.08
            if status != "War" and relation <= -42 and conflict_pressure > 4 and year > 8:
                self.statuses[key] = "War"
                self.active_wars[key] = {
                    "started": year,
                    "duration": 0,
                    "intensity": min(2.4, 0.8 + conflict_pressure / 35 + military_gap),
                    "cause": self._main_conflict_resource(civ_a, civ_b, market_prices),
                }
                self.events.append({
                    "year": year,
                    "civilization": "Geopolitics",
                    "event": f"{civ_a.name} and {civ_b.name} entered a resource war over {self.active_wars[key]['cause']}."
                })
            elif status == "War":
                continue
            elif relation >= 45:
                if status != "Alliance":
                    self.events.append({
                        "year": year,
                        "civilization": "Diplomacy",
                        "event": f"{civ_a.name} and {civ_b.name} signed a defensive alliance."
                    })
                self.statuses[key] = "Alliance"
            elif relation <= -30:
                if status != "Rivalry":
                    self.events.append({
                        "year": year,
                        "civilization": "Diplomacy",
                        "event": f"{civ_a.name} and {civ_b.name} became strategic rivals."
                    })
                self.statuses[key] = "Rivalry"
            elif relation > 12 and status == "Rivalry":
                self.statuses[key] = "Treaty"
                self.treaties[key] = 25
                self.events.append({
                    "year": year,
                    "civilization": "Diplomacy",
                    "event": f"{civ_a.name} and {civ_b.name} signed a 25-year normalization treaty."
                })
            elif status not in ["Alliance", "Treaty"]:
                self.statuses[key] = "Neutral"

    def _resolve_existing_wars(self, year: int, civilizations: list, world_map) -> None:
        civ_by_id = {c.id: c for c in civilizations}
        ended = []
        for key, war in list(self.active_wars.items()):
            a_id, b_id = key
            a, b = civ_by_id[a_id], civ_by_id[b_id]
            war["duration"] += 1
            intensity = war["intensity"]
            a_loss = min(a.military * 0.018 * intensity, a.military * 0.08)
            b_loss = min(b.military * 0.018 * intensity, b.military * 0.08)
            a.military = max(50, a.military - b_loss * 0.55)
            b.military = max(50, b.military - a_loss * 0.55)
            a.stability = max(0, a.stability - 0.06 * intensity)
            b.stability = max(0, b.stability - 0.06 * intensity)

            if war["duration"] % 9 == 0:
                winner, loser = (a, b) if a.power_score >= b.power_score else (b, a)
                self._transfer_border_tile(winner, loser, world_map)

            if war["duration"] >= 36 or min(a.stability, b.stability) < 30:
                winner, loser = (a, b) if a.power_score >= b.power_score else (b, a)
                self.relations[key] = -15
                self.statuses[key] = "Treaty"
                self.treaties[key] = 35
                ended.append(key)
                self.events.append({
                    "year": year,
                    "civilization": "War",
                    "event": f"{winner.name} forced {loser.name} into a peace treaty after {war['duration']} years of conflict."
                })
        for key in ended:
            self.active_wars.pop(key, None)

    def _transfer_border_tile(self, winner, loser, world_map) -> None:
        loser_tiles = list(loser.territory)
        if not loser_tiles:
            return
        border_tiles = []
        winner_territory = winner.territory
        for x, y in loser_tiles:
            tile = world_map.get_tile(x, y)
            if tile is None:
                continue
            for neighbor in world_map.neighbors(tile):
                if (neighbor.x, neighbor.y) in winner_territory:
                    border_tiles.append(tile)
                    break
        if not border_tiles:
            border_tiles = [world_map.get_tile(*loser_tiles[0])]
        target = max(border_tiles, key=lambda t: t.total_resources)
        loser.territory.discard((target.x, target.y))
        winner.territory.add((target.x, target.y))
        target.owner_id = winner.id
        target.city_id = None

    def _trade_compatibility(self, civ_a, civ_b) -> float:
        score = 0.0
        for resource in RESOURCE_COLUMNS:
            score += min(civ_a.exports.get(resource, 0), civ_b.imports.get(resource, 0))
            score += min(civ_b.exports.get(resource, 0), civ_a.imports.get(resource, 0))
        return score

    def _resource_competition(self, civ_a, civ_b, prices: dict) -> float:
        score = 0.0
        for resource in RESOURCE_COLUMNS:
            shared_import_need = min(civ_a.imports.get(resource, 0), civ_b.imports.get(resource, 0))
            price_weight = prices.get(resource, 1.0)
            score += shared_import_need * price_weight
        return score

    def _border_pressure(self, civ_a, civ_b, world_map) -> float:
        pressure = 0
        b_tiles = civ_b.territory
        for x, y in civ_a.territory:
            tile = world_map.get_tile(x, y)
            if tile is None:
                continue
            for neighbor in world_map.neighbors(tile):
                if (neighbor.x, neighbor.y) in b_tiles:
                    pressure += 1
        return pressure

    def _power_fear(self, civ_a, civ_b) -> float:
        return abs(civ_a.power_score - civ_b.power_score) / max(civ_a.power_score + civ_b.power_score, 1) * 100

    def _main_conflict_resource(self, civ_a, civ_b, prices: dict) -> str:
        scores = {}
        for resource in RESOURCE_COLUMNS:
            scores[resource] = min(civ_a.imports.get(resource, 0), civ_b.imports.get(resource, 0)) * prices.get(resource, 1)
        resource = max(scores, key=scores.get)
        return resource.title()
