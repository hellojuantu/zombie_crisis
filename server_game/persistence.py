"""Game state persistence — save/load to a local JSON file."""

import json
import time
from pathlib import Path

SAVE_DIR = Path.home() / ".zombie"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
SAVE_PATH = SAVE_DIR / "save.json"

_PLAYER_FIELDS = [
    "level", "xp", "score", "kills",
    "materials", "lore",
    "hp", "max_hp",
    "lives", "max_lives",
    "weapon_id", "weapon_level", "weapons",
    "ammo_reserve", "talents",
]


def save_game(game):
    players_out = {}
    for player in game.players.values():
        idx = player.get("idx", 0)
        entry = {f: player.get(f) for f in _PLAYER_FIELDS if player.get(f) is not None}
        players_out[str(idx)] = entry

    data = {
        "version": 1,
        "wave": game.wave,
        "peak_players": game._peak_players,
        "players": players_out,
        "saved_at": time.time(),
    }
    SAVE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_game():
    if not SAVE_PATH.exists():
        return None
    try:
        data = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
        if data.get("version") != 1:
            return None
        return data
    except Exception:
        return None


def apply_saved_player(player, saved_players):
    idx = str(player.get("idx", 0))
    saved = saved_players.get(idx)
    if not saved:
        return
    for field in _PLAYER_FIELDS:
        if field in saved and saved[field] is not None:
            player[field] = saved[field]
    player["dead"] = False
    player["vx"] = 0
    player["vy"] = 0
