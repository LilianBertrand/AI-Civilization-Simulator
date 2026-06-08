RESOURCE_COLUMNS = ["food", "wood", "stone", "iron", "gold"]

class EconomyEngine:
    def update_civilization(self, civ, world_map, prices=None):
        prices = prices or {"food": 1.0, "wood": 2.0, "stone": 3.0, "iron": 8.0, "gold": 25.0}
        owned_tiles = [world_map.get_tile(x, y) for x, y in civ.territory]
        owned_tiles = [t for t in owned_tiles if t is not None]

        production = {res: sum(getattr(t, res) for t in owned_tiles) for res in RESOURCE_COLUMNS}

        # Technology improves extraction and agriculture.
        tech_multiplier = 1 + civ.technology * 0.035
        production = {res: value * tech_multiplier for res, value in production.items()}

        food_consumption = civ.population * 0.012
        demand = {
            "food": food_consumption,
            "wood": len(civ.territory) * 0.28 + civ.population * 0.0015,
            "stone": len(civ.territory) * 0.18 + civ.population * 0.0008,
            "iron": civ.military * 0.012 + civ.population * 0.0004,
            "gold": civ.wealth * 0.0009 + civ.population * 0.0003,
        }

        if civ.personality == "militarist":
            demand["iron"] *= 1.35
            demand["food"] *= 1.08
        elif civ.personality == "merchant":
            demand["gold"] *= 1.25
            demand["wood"] *= 1.12
        elif civ.personality == "scientific":
            demand["stone"] *= 1.12
            demand["gold"] *= 1.10
        elif civ.personality == "expansionist":
            demand["wood"] *= 1.20
            demand["stone"] *= 1.18

        if getattr(civ, "at_war", False):
            war_multiplier = 1 + min(0.75, getattr(civ, "war_pressure", 0.0) * 0.28)
            demand["iron"] *= war_multiplier
            demand["food"] *= 1 + min(0.25, getattr(civ, "war_pressure", 0.0) * 0.10)
            demand["wood"] *= 1 + min(0.20, getattr(civ, "war_pressure", 0.0) * 0.08)

        revenue = sum(production[res] * prices[res] for res in RESOURCE_COLUMNS)
        consumption_cost = sum(demand[res] * prices[res] for res in RESOURCE_COLUMNS)
        trade_balance = revenue - consumption_cost

        civ.production = production
        civ.demand = demand
        civ.trade_balance = trade_balance
        civ.exports = {res: max(0, production[res] - demand[res]) for res in RESOURCE_COLUMNS}
        civ.imports = {res: max(0, demand[res] - production[res]) for res in RESOURCE_COLUMNS}

        food_balance = production["food"] - demand["food"]
        civ.food_stock = max(0, civ.food_stock + food_balance)
        civ.yearly_food = production["food"]
        civ.yearly_wealth = revenue
        civ.wealth = max(0, civ.wealth + trade_balance * 0.10)

        if food_balance > 0:
            civ.population *= 1.0 + min(0.035, 0.008 + food_balance / max(civ.population, 1) * 0.03)
            civ.stability = min(100, civ.stability + 0.10)
        else:
            civ.population *= 0.990
            civ.stability = max(0, civ.stability - 0.50)

        if trade_balance < 0:
            civ.stability = max(0, civ.stability - min(0.25, abs(trade_balance) / 20000))

        civ.military += max(0, civ.wealth) * 0.0015
        civ.technology += 0.004 + (max(civ.wealth, 0) / 250000)
