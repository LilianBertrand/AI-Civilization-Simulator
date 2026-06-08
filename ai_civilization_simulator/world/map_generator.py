import numpy as np
import pandas as pd
from world.terrain import Tile

TERRAIN_TYPES = ["water", "plains", "forest", "mountain", "desert"]

RESOURCE_PROFILE = {
    "water":    {"food": 0.4, "wood": 0.0, "stone": 0.0, "iron": 0.0, "gold": 0.0},
    "plains":   {"food": 2.4, "wood": 0.6, "stone": 0.2, "iron": 0.1, "gold": 0.05},
    "forest":   {"food": 1.3, "wood": 2.5, "stone": 0.3, "iron": 0.1, "gold": 0.05},
    "mountain": {"food": 0.3, "wood": 0.4, "stone": 2.5, "iron": 1.5, "gold": 0.5},
    "desert":   {"food": 0.4, "wood": 0.1, "stone": 0.8, "iron": 0.4, "gold": 0.6},
}

class WorldMap:
    def __init__(self, width: int, height: int, seed: int | None = None):
        self.width = width
        self.height = height
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.tiles: list[Tile] = []
        self.generate()

    def generate(self) -> None:
        """Generate a replayable but genuinely different world for each seed.

        The previous generator was mostly independent random noise, so many worlds
        felt similar. This version creates continent-like terrain and resource
        clusters so every run has a different strategic geography.
        """
        self.tiles = []
        center_x = self.rng.uniform(0.38, 0.62)
        center_y = self.rng.uniform(0.36, 0.64)
        mountain_band = self.rng.uniform(0.18, 0.82)
        desert_band = self.rng.uniform(0.20, 0.80)

        for y in range(self.height):
            for x in range(self.width):
                nx = x / max(self.width - 1, 1)
                ny = y / max(self.height - 1, 1)
                dist = ((nx - center_x) ** 2 + (ny - center_y) ** 2) ** 0.5
                coastal_bias = 0.33 if x < 3 or y < 3 or x > self.width - 4 or y > self.height - 4 else 0.0
                continent_score = 0.68 - dist + self.rng.normal(0, 0.11) - coastal_bias

                if continent_score < 0.18:
                    terrain = "water"
                else:
                    mountain_score = abs((nx + 0.35 * ny) - mountain_band) + self.rng.normal(0, 0.04)
                    desert_score = abs((ny - 0.25 * nx) - desert_band) + self.rng.normal(0, 0.05)
                    humidity = self.rng.random() + 0.35 * (1 - abs(ny - 0.5))
                    if mountain_score < 0.075:
                        terrain = "mountain"
                    elif desert_score < 0.085 and humidity < 0.75:
                        terrain = "desert"
                    elif humidity > 0.78:
                        terrain = "forest"
                    else:
                        terrain = "plains"

                base = RESOURCE_PROFILE[terrain]
                noise = {k: max(0.0, v * self.rng.normal(1.0, 0.35)) for k, v in base.items()}

                # Strategic clusters: rare deposits and fertile zones make maps
                # asymmetric, giving each simulation different winners.
                if terrain == "mountain" and self.rng.random() < 0.12:
                    noise["iron"] *= self.rng.uniform(2.2, 4.2)
                    noise["gold"] *= self.rng.uniform(1.4, 3.0)
                if terrain in {"plains", "forest"} and self.rng.random() < 0.10:
                    noise["food"] *= self.rng.uniform(1.7, 3.2)
                if terrain == "forest" and self.rng.random() < 0.11:
                    noise["wood"] *= self.rng.uniform(1.8, 3.3)
                if terrain == "desert" and self.rng.random() < 0.09:
                    noise["gold"] *= self.rng.uniform(2.0, 4.8)

                self.tiles.append(Tile(x=x, y=y, terrain=terrain, **noise))

    def get_tile(self, x: int, y: int) -> Tile | None:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return None
        return self.tiles[y * self.width + x]

    def neighbors(self, tile: Tile) -> list[Tile]:
        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        return [t for dx, dy in offsets if (t := self.get_tile(tile.x + dx, tile.y + dy)) is not None]

    def habitable_unowned_tiles(self) -> list[Tile]:
        return [t for t in self.tiles if t.is_habitable and t.owner_id is None]

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([tile.__dict__ | {"total_resources": tile.total_resources} for tile in self.tiles])
