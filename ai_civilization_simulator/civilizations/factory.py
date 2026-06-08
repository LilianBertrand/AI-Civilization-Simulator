import numpy as np
from civilizations.civilization import Civilization
from config.settings import CIV_COLORS

CIV_NAMES = [
    "Aurelian Empire", "Solkar Republic", "Nymer Kingdom", "Eldran League",
    "Varok Tribes", "Thalor Dominion", "Oriven Cities", "Kairon Realm",
    "Myridian Union", "Zarok Khanate", "Veloria Compact", "Arkan Federation"
]

PERSONALITIES = ["militarist", "merchant", "scientific", "religious", "expansionist", "balanced"]

PERSONALITY_BONUSES = {
    "militarist": {"military": 1.35, "wealth": 0.95, "technology": 1.00},
    "merchant": {"military": 0.95, "wealth": 1.35, "technology": 1.05},
    "scientific": {"military": 0.90, "wealth": 1.05, "technology": 1.35},
    "religious": {"military": 1.05, "wealth": 1.00, "technology": 1.05, "stability": 1.20},
    "expansionist": {"military": 1.15, "wealth": 1.05, "technology": 0.95},
    "balanced": {"military": 1.00, "wealth": 1.00, "technology": 1.00},
}

def create_civilizations(world_map, count: int, seed: int | None = None) -> list[Civilization]:
    rng = np.random.default_rng(seed)
    candidates = world_map.habitable_unowned_tiles()
    rng.shuffle(candidates)
    selected = []

    # Do not always pick the richest tiles: strong starts still matter, but
    # geography, distance and random shocks make each run less deterministic.
    candidates = sorted(
        candidates,
        key=lambda t: (0.65 * t.total_resources) + rng.normal(0, 1.8),
        reverse=True,
    )

    min_distance = max(5, int((world_map.width + world_map.height) / max(count, 4) / 2.4))
    for tile in candidates:
        if len(selected) >= count:
            break
        if all(abs(tile.x - other.x) + abs(tile.y - other.y) > min_distance for other in selected):
            selected.append(tile)

    if len(selected) < count:
        for tile in candidates:
            if len(selected) >= count:
                break
            if tile not in selected:
                selected.append(tile)

    name_pool = list(CIV_NAMES)
    personality_pool = list(PERSONALITIES)
    rng.shuffle(name_pool)
    rng.shuffle(personality_pool)

    civilizations = []
    for i, tile in enumerate(selected):
        personality = personality_pool[i % len(personality_pool)]
        civ = Civilization(
            id=i,
            name=name_pool[i % len(name_pool)],
            color=CIV_COLORS[i % len(CIV_COLORS)],
            personality=personality,
            capital_x=tile.x,
            capital_y=tile.y,
        )
        bonus = PERSONALITY_BONUSES[personality]
        civ.population *= rng.uniform(0.82, 1.22)
        civ.food_stock *= rng.uniform(0.75, 1.35)
        civ.military *= bonus.get("military", 1.0) * rng.uniform(0.75, 1.30)
        civ.wealth *= bonus.get("wealth", 1.0) * rng.uniform(0.72, 1.38)
        civ.technology *= bonus.get("technology", 1.0) * rng.uniform(0.82, 1.24)
        civ.stability *= bonus.get("stability", 1.0) * rng.uniform(0.82, 1.16)
        civ.stability = min(95, max(38, civ.stability))
        civ.territory.add((tile.x, tile.y))
        tile.owner_id = civ.id
        tile.city_id = civ.id
        civilizations.append(civ)

    return civilizations
