from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

RESOURCE_COLUMNS = ["food", "wood", "stone", "iron", "gold"]

BASE_PRICES = {
    "food": 1.0,
    "wood": 2.0,
    "stone": 3.0,
    "iron": 8.0,
    "gold": 25.0,
}

PRICE_FLOORS = {
    "food": 0.35,
    "wood": 0.75,
    "stone": 1.0,
    "iron": 2.5,
    "gold": 10.0,
}

PRICE_CEILINGS = {
    "food": 6.0,
    "wood": 12.0,
    "stone": 18.0,
    "iron": 45.0,
    "gold": 90.0,
}

@dataclass
class MarketEngine:
    """Global commodity market driven by simulated supply and demand."""

    prices: Dict[str, float] = field(default_factory=lambda: BASE_PRICES.copy())
    history: List[dict] = field(default_factory=list)
    latest_market: Dict[str, dict] = field(default_factory=dict)
    events: List[dict] = field(default_factory=list)

    def update(self, year: int, civilizations: list) -> None:
        world_supply = {resource: 0.0 for resource in RESOURCE_COLUMNS}
        world_demand = {resource: 0.0 for resource in RESOURCE_COLUMNS}

        for civ in civilizations:
            for resource in RESOURCE_COLUMNS:
                world_supply[resource] += civ.production.get(resource, 0.0)
                world_demand[resource] += civ.demand.get(resource, 0.0)

        commodity_index = 0.0
        market_rows = {}

        for resource in RESOURCE_COLUMNS:
            supply = max(world_supply[resource], 0.01)
            demand = max(world_demand[resource], 0.01)
            imbalance = (demand - supply) / supply
            old_price = self.prices[resource]

            # Smooth price adjustment: scarcity increases price, surplus lowers it.
            # Phase 3 premium fix: cap yearly moves to avoid unreadable early spikes.
            price_change = max(-0.12, min(0.12, imbalance * 0.18))
            new_price = old_price * (1 + price_change)
            new_price = max(PRICE_FLOORS[resource], min(PRICE_CEILINGS[resource], new_price))
            self.prices[resource] = new_price

            commodity_index += new_price / BASE_PRICES[resource] * 100
            market_rows[resource] = {
                "year": year,
                "resource": resource,
                "supply": supply,
                "demand": demand,
                "surplus_deficit": supply - demand,
                "price": new_price,
                "price_change_pct": ((new_price / old_price) - 1) * 100,
            }

            if abs(market_rows[resource]["price_change_pct"]) >= 12:
                direction = "surged" if market_rows[resource]["price_change_pct"] > 0 else "fell"
                reason = "scarcity pressure" if direction == "surged" else "excess supply"
                self.events.append({
                    "year": year,
                    "civilization": "Global Market",
                    "event": f"{resource.title()} prices {direction} by {abs(market_rows[resource]['price_change_pct']):.1f}% due to {reason}."
                })

        commodity_index = commodity_index / len(RESOURCE_COLUMNS)
        self.latest_market = market_rows

        self.history.append({
            "year": year,
            "commodity_index": commodity_index,
            **{f"{resource}_price": self.prices[resource] for resource in RESOURCE_COLUMNS},
            **{f"{resource}_price_index": (self.prices[resource] / BASE_PRICES[resource]) * 100 for resource in RESOURCE_COLUMNS},
            **{f"{resource}_supply": world_supply[resource] for resource in RESOURCE_COLUMNS},
            **{f"{resource}_demand": world_demand[resource] for resource in RESOURCE_COLUMNS},
        })

    def market_dataframe(self) -> pd.DataFrame:
        if not self.latest_market:
            return pd.DataFrame()
        df = pd.DataFrame(self.latest_market.values())
        df["resource"] = df["resource"].str.title()
        return df.rename(columns={
            "resource": "Resource",
            "supply": "Supply",
            "demand": "Demand",
            "surplus_deficit": "Surplus / Deficit",
            "price": "Price",
            "price_change_pct": "Price Change %",
        })

    def history_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.history)
