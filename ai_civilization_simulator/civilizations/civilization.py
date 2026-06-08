from dataclasses import dataclass, field

@dataclass
class Civilization:
    id: int
    name: str
    color: str
    personality: str
    capital_x: int
    capital_y: int
    population: float = 1000.0
    food_stock: float = 500.0
    wealth: float = 250.0
    military: float = 100.0
    technology: float = 1.0
    stability: float = 75.0
    territory: set[tuple[int, int]] = field(default_factory=set)
    yearly_food: float = 0.0
    yearly_wealth: float = 0.0
    production: dict = field(default_factory=dict)
    demand: dict = field(default_factory=dict)
    exports: dict = field(default_factory=dict)
    imports: dict = field(default_factory=dict)
    trade_balance: float = 0.0
    allies: set[int] = field(default_factory=set)
    rivals: set[int] = field(default_factory=set)
    enemies: set[int] = field(default_factory=set)
    at_war: bool = False
    war_pressure: float = 0.0

    @property
    def power_score(self) -> float:
        return (
            self.population * 0.30
            + self.wealth * 0.90
            + self.military * 2.0
            + self.technology * 250
            + self.stability * 12
            + len(self.territory) * 50
        )

    @property
    def gdp(self) -> float:
        return self.wealth + self.yearly_wealth * 8 + self.population * 0.35 + self.technology * 400
