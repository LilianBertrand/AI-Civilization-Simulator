from dataclasses import dataclass

@dataclass
class Tile:
    x: int
    y: int
    terrain: str
    food: float
    wood: float
    stone: float
    iron: float
    gold: float
    owner_id: int | None = None
    city_id: int | None = None

    @property
    def is_habitable(self) -> bool:
        return self.terrain != "water"

    @property
    def total_resources(self) -> float:
        return self.food + self.wood + self.stone + self.iron + self.gold
