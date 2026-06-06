"""Authoritative zombie shooter simulation."""

import math
import random
import time

from .config import (
    BULLET_DAMAGE,
    BULLET_LIFE,
    BULLET_R,
    BULLET_SPEED,
    BASE_DAMAGE_ALERT_CD,
    BASE_MAX_HP,
    BASE_OBSTACLE_CLEARANCE,
    BASE_R,
    BASE_REPAIR_PER_PLAYER,
    BASE_REPAIR_PER_WAVE,
    BASE_REVIVE_DELAY,
    BASE_REVIVE_HP_PCT,
    BASE_TARGET_BIAS,
    BASE_X,
    BASE_Y,
    BLOATER_BASE_DAMAGE,
    BLOATER_PLAYER_DAMAGE,
    BLOATER_RADIUS,
    BLOATER_ZOMBIE_DAMAGE,
    BOSS_WAVE_INTERVAL,
    COMBO_RAPID_BONUS_AT,
    COMBO_SHIELD_BONUS_AT,
    COMBO_SPREAD_BONUS_AT,
    COMBO_WINDOW,
    DASH_CD,
    DASH_DIST,
    DIRECTOR_CHECK_DT,
    DIRECTOR_LEASH_AFTER,
    DIRECTOR_LEASH_RADIUS,
    DIRECTOR_MAX_NEAR_ZOMBIES,
    DIRECTOR_MAX_PRESSURE_SPAWNS,
    DIRECTOR_MIN_NEAR_ZOMBIES,
    DIRECTOR_NEAR_ZOMBIES_PER_PLAYER,
    FIRE_INTERVAL,
    INITIAL_ITEMS,
    INITIAL_ZOMBIES,
    INPUT_IDLE_TIMEOUT,
    INTEREST_RADIUS,
    ITEM_R,
    ITEM_SPAWN_DT,
    BULLET_INTEREST_RADIUS,
    EVENT_INTEREST_RADIUS,
    EXTRACTION_CAPTURE_SECONDS,
    EXTRACTION_COUNT,
    EXTRACTION_DISCOVER_RADIUS,
    ITEM_TYPES,
    ITEM_INTEREST_RADIUS,
    LEADERBOARD_SIZE,
    LEAPER_COOLDOWN,
    LEAPER_MAX_RANGE,
    LEAPER_MIN_RANGE,
    LEAPER_SPEED_MULT,
    LEVEL_XP_BASE,
    MAP_H,
    MAP_W,
    MAX_BULLETS,
    MAX_ITEMS,
    MAX_SYNC_BULLETS_PER_CLIENT,
    MAX_SYNC_ITEMS_PER_CLIENT,
    MAX_SYNC_PLAYERS_PER_CLIENT,
    MAX_SYNC_ZOMBIES_PER_CLIENT,
    MAX_ZOMBIES,
    MAZE_CELL,
    MAZE_COLS,
    MAZE_EXTRA_LINKS,
    MAZE_ROWS,
    MAZE_SAFE_JITTER,
    MAZE_WALL,
    MISSION_CAPTURE_RADIUS,
    MISSION_CAPTURE_SECONDS,
    MISSION_DISCOVER_RADIUS,
    MISSION_MAX_DIST,
    MISSION_MIN_DIST,
    MISSION_REPAIR_AMOUNT,
    MISSION_REWARD_SCORE,
    MISSION_REWARD_XP,
    MOVE_ACCEL,
    MOVE_DECEL,
    NUKE_RADIUS,
    PLAYER_MAX_HP,
    PLAYER_INTEREST_RADIUS,
    PLAYER_R,
    PLAYER_SPD,
    PLAYER_STALE_TIMEOUT,
    PRESSURE_SPAWN_MAX_DIST,
    PRESSURE_SPAWN_MIN_DIST,
    PROTECT,
    PROTOCOL_VERSION,
    RAPID_FIRE_MULT,
    SERVER_DT,
    SERVER_TICK_HZ,
    SCREAMER_COOLDOWN,
    SCREAMER_RADIUS,
    SCREAMER_RALLY_MULT,
    SCREAMER_RALLY_SECONDS,
    SNAPSHOT_HZ,
    SPATIAL_CELL,
    SPREAD_ANGLE,
    STORY_BEATS,
    TASK_DROP_CHANCE,
    TASK_PICKUPS_PER_STAGE,
    WAVE_BASE,
    WAVE_BURST_BASE,
    WAVE_BURST_MAX,
    WAVE_BURST_PER_PLAYER,
    WAVE_STEP,
    ZOMBIE_STUCK_AFTER,
    ZOMBIE_STUCK_EPS,
    ZOMBIE_SPAWN_DT,
    ZOMBIE_INTEREST_RADIUS,
    ZOMBIE_TYPES,
)
from .geometry import (
    approach,
    circ_rect,
    clamp,
    finite_float,
    normalize_input,
    player_color,
    player_name,
    pt_in_rect,
)


def player_speed(level=1):
    return PLAYER_SPD + min(38, max(0, level - 1) * 3.5)


def zombie_speed(ztype, wave):
    meta = ZOMBIE_TYPES[ztype]
    return meta["speed"] * (1 + min(0.34, max(0, wave - 1) * 0.025))


class Game:
    def __init__(self, emitter=None):
        self.emit = emitter
        self.players = {}
        self.zombies = {}
        self.bullets = {}
        self.items = {}
        self.obstacles = []
        self.obstacle_grid = {}
        self.base = None
        self.floor_points = []
        self.spawn_point = (BASE_X, BASE_Y)
        self.extract_point = (BASE_X, BASE_Y)
        self.extractions = []
        self.task_counts = {"fuse": 0, "sample": 0, "keycard": 0}
        self.mission = None
        self._next_z = 1
        self._next_b = 1
        self._next_i = 1
        self.wave = 1
        self.wave_remaining = self._wave_budget()
        self.wave_kills = 0
        self.wave_announced = False
        self.zombie_spawn_timer = 0.0
        self.item_spawn_timer = 0.0
        self.director_timer = 0.0
        self.running = False
        self.last_tick = time.monotonic()
        self.tick_id = 0
        self.perf = {
            "tick_ms": 0.0,
            "snap_ms": 0.0,
            "sync_ms": 0.0,
            "players": 0,
            "zombies": 0,
            "bullets": 0,
            "items": 0,
        }
        self._gen_obstacles()
        self._start_stage_tasks()
        for _ in range(min(INITIAL_ZOMBIES, self.wave_remaining)):
            if self.spawn_zombie(emit=False):
                self.wave_remaining -= 1
        for _ in range(INITIAL_ITEMS):
            self.spawn_item(emit=False)

    def _wave_budget(self):
        return WAVE_BASE + (self.wave - 1) * WAVE_STEP

    def _base_down(self, now=None):
        return False

    def _repair_base(self, amount, now, reason="repair"):
        return

    def _base_snapshot(self, now=None):
        return None

    def _safe_objective_point(self):
        return self.extract_point

    def _task_summary(self):
        return {
            "fuse": self.task_counts.get("fuse", 0),
            "sample": self.task_counts.get("sample", 0),
            "keycard": self.task_counts.get("keycard", 0),
        }

    def _requires_text(self, requires):
        names = {"fuse": "保险丝", "sample": "病毒样本", "keycard": "门禁卡"}
        parts = []
        for typ, needed in requires.items():
            have = self.task_counts.get(typ, 0)
            parts.append(f"{names.get(typ, typ)} {have}/{needed}")
        return " · ".join(parts) if parts else "无需额外物资"

    def _exit_ready(self, exit_point):
        return all(self.task_counts.get(typ, 0) >= needed for typ, needed in exit_point.get("requires", {}).items())

    def _new_extractions(self):
        far_points = sorted(
            self.floor_points or [self.extract_point],
            key=lambda p: (p[0] - self.spawn_point[0]) ** 2 + (p[1] - self.spawn_point[1]) ** 2,
            reverse=True,
        )
        selected = []
        for point in far_points:
            if all(math.hypot(point[0] - old[0], point[1] - old[1]) > MAZE_CELL * 1.4 for old in selected):
                selected.append(point)
            if len(selected) >= EXTRACTION_COUNT:
                break
        while len(selected) < EXTRACTION_COUNT:
            selected.append(far_points[len(selected) % max(1, len(far_points))])

        templates = [
            ("service", "维修通道", {"fuse": 2}, "找到保险丝，恢复卷帘门供电"),
            ("lab", "净化闸门", {"sample": 3}, "击杀感染体取得样本，骗过净化扫描"),
            ("security", "安保电梯", {"keycard": 1, "sample": 1}, "夺取门禁卡并提交一份样本"),
        ]
        exits = []
        for idx, (point, spec) in enumerate(zip(selected, templates)):
            typ, name, requires, text = spec
            exits.append({
                "id": f"{typ}-{self.wave}",
                "type": typ,
                "name": name,
                "text": text,
                "requires": dict(requires),
                "x": point[0],
                "y": point[1],
                "radius": MISSION_CAPTURE_RADIUS,
                "charge": 0.0,
                "visible": False,
                "done": False,
                "wave": self.wave,
                "color": ("#66d9ff", "#b7ff47", "#d98cff")[idx],
            })
        return exits

    def _start_stage_tasks(self):
        self.task_counts = {"fuse": 0, "sample": 0, "keycard": 0}
        self.extractions = self._new_extractions()
        self.mission = self.extractions[0] if self.extractions else None
        for _ in range(TASK_PICKUPS_PER_STAGE):
            self.spawn_item(item_type="fuse", emit=False)

    def _new_mission(self):
        self.extractions = self._new_extractions()
        self.mission = self.extractions[0] if self.extractions else None
        return self.mission

    def _extraction_snapshot(self, exit_point, full=True):
        payload = {
            "id": exit_point.get("id"),
            "type": exit_point.get("type", "exit"),
            "x": round(exit_point.get("x", 0), 1),
            "y": round(exit_point.get("y", 0), 1),
            "radius": exit_point.get("radius", MISSION_CAPTURE_RADIUS),
            "charge": round(max(0, min(1, exit_point.get("charge", 0))), 3),
            "done": bool(exit_point.get("done")),
            "visible": bool(exit_point.get("visible")),
            "ready": self._exit_ready(exit_point),
            "requires": dict(exit_point.get("requires", {})),
            "task": self._task_summary(),
            "color": exit_point.get("color", "#ff4d7a"),
            "wave": exit_point.get("wave", self.wave),
        }
        if full:
            payload.update({
                "name": exit_point.get("name", "撤离点"),
                "text": exit_point.get("text", ""),
                "requireText": self._requires_text(exit_point.get("requires", {})),
            })
        return payload

    def _extractions_snapshot(self, full=True):
        return [self._extraction_snapshot(exit_point, full=full) for exit_point in self.extractions]

    def _mission_snapshot(self, full=True):
        visible = [exit_point for exit_point in self.extractions if exit_point.get("visible") or exit_point.get("charge", 0) > 0]
        mission = self.mission or (visible[0] if visible else (self.extractions[0] if self.extractions else None))
        if not mission:
            return None
        return self._extraction_snapshot(mission, full=full)

    def _is_boss_wave(self):
        return self.wave > 0 and self.wave % BOSS_WAVE_INTERVAL == 0

    def _story_for_wave(self):
        beat = STORY_BEATS[(self.wave - 1) % len(STORY_BEATS)]
        return beat.format(wave=self.wave)

    def _objective_snapshot(self, full=True):
        budget = max(1, self._wave_budget())
        remaining = max(0, self.wave_remaining + len(self.zombies))
        killed = max(0, min(budget, budget - remaining))
        boss_alive = any(zombie.get("type") == "boss" for zombie in self.zombies.values())
        visible_exits = [exit_point for exit_point in self.extractions if exit_point.get("visible")]
        ready_exits = [exit_point for exit_point in visible_exits if self._exit_ready(exit_point)]
        charging = next((exit_point for exit_point in self.extractions if exit_point.get("charge", 0) > 0), None)
        task = self._task_summary()
        if charging:
            title = charging["name"]
            if self._exit_ready(charging):
                text = f"撤离门开启 {round(charging['charge'] * 100)}% · 别离开光圈"
            else:
                text = f"条件不足：{self._requires_text(charging.get('requires', {}))}"
        elif ready_exits:
            title = "可撤离"
            text = f"{ready_exits[0]['name']} 条件满足，进入光圈撤离"
        elif boss_alive:
            title = "重型感染体"
            text = "它身上可能有门禁卡，打倒它再撤"
        elif visible_exits:
            title = "撤离点已发现"
            text = f"{visible_exits[0]['name']}：{self._requires_text(visible_exits[0].get('requires', {}))}"
        else:
            title = "搜寻撤离点"
            text = f"保险丝 {task['fuse']} · 样本 {task['sample']} · 门禁卡 {task['keycard']} · 感染体 {remaining}"
        progress = charging.get("charge", 0) if charging else min(1, killed / budget)
        payload = {
            "remaining": remaining,
            "budget": budget,
            "progress": round(max(0, min(1, progress)), 3),
            "boss": self._is_boss_wave() or boss_alive,
            "task": task,
            "visibleExits": len(visible_exits),
            "readyExits": len(ready_exits),
        }
        if full:
            payload.update({
                "title": title,
                "text": text,
                "story": self._story_for_wave(),
            })
        return payload

    def reset(self, keep_players=False):
        old_sids = list(self.players.keys()) if keep_players else []
        self.__init__(emitter=self.emit)
        for sid in old_sids:
            self.add_player(sid)
        self.running = bool(self.players)

    def _emit(self, event, data):
        if self.emit:
            self.emit(event, data)

    def _emit_to(self, event, data, targets):
        if not self.emit:
            return
        clean_targets = [sid for sid in dict.fromkeys(targets) if sid in self.players]
        if not clean_targets:
            return
        payload = dict(data)
        payload["_targets"] = clean_targets
        self.emit(event, payload)

    def _emit_near(self, event, data, x, y, radius=EVENT_INTEREST_RADIUS, include=None):
        targets = []
        for sid, player in self.players.items():
            if math.hypot(player["x"] - x, player["y"] - y) <= radius:
                targets.append(sid)
        if include:
            targets.append(include)
        self._emit_to(event, data, targets)

    def _now(self):
        return time.monotonic()

    def _record_tick_perf(self, started):
        elapsed = (time.perf_counter() - started) * 1000
        old = self.perf.get("tick_ms", 0.0)
        self.perf["tick_ms"] = elapsed if old <= 0 else old * 0.85 + elapsed * 0.15
        self.perf["players"] = len(self.players)
        self.perf["zombies"] = len(self.zombies)
        self.perf["bullets"] = len(self.bullets)
        self.perf["items"] = len(self.items)

    def _record_snapshot_perf(self, started):
        elapsed = (time.perf_counter() - started) * 1000
        old = self.perf.get("snap_ms", 0.0)
        self.perf["snap_ms"] = elapsed if old <= 0 else old * 0.85 + elapsed * 0.15

    def _perf_snapshot(self):
        return {
            "tick_ms": round(self.perf.get("tick_ms", 0.0), 2),
            "snap_ms": round(self.perf.get("snap_ms", 0.0), 2),
            "sync_ms": round(self.perf.get("sync_ms", 0.0), 2),
            "players": len(self.players),
            "zombies": len(self.zombies),
            "bullets": len(self.bullets),
            "items": len(self.items),
            "snapshot_hz": SNAPSHOT_HZ,
        }

    def _gen_obstacles(self):
        self.obstacles = []
        margin_x = (MAP_W - MAZE_COLS * MAZE_CELL) / 2
        margin_y = (MAP_H - MAZE_ROWS * MAZE_CELL) / 2
        start = (0, MAZE_ROWS // 2)
        visited = {start}
        openings = {start: set()}
        stack = [start]

        def neighbors(cell):
            c, r = cell
            result = []
            if c > 0:
                result.append(("W", (c - 1, r), "E"))
            if c < MAZE_COLS - 1:
                result.append(("E", (c + 1, r), "W"))
            if r > 0:
                result.append(("N", (c, r - 1), "S"))
            if r < MAZE_ROWS - 1:
                result.append(("S", (c, r + 1), "N"))
            random.shuffle(result)
            return result

        while stack:
            cell = stack[-1]
            candidates = [(d, nxt, back) for d, nxt, back in neighbors(cell) if nxt not in visited]
            if not candidates:
                stack.pop()
                continue
            direction, nxt, back = candidates[0]
            openings.setdefault(cell, set()).add(direction)
            openings.setdefault(nxt, set()).add(back)
            visited.add(nxt)
            stack.append(nxt)

        for _ in range(MAZE_EXTRA_LINKS + min(10, self.wave)):
            cell = (random.randrange(MAZE_COLS), random.randrange(MAZE_ROWS))
            direction, nxt, back = random.choice(neighbors(cell))
            openings.setdefault(cell, set()).add(direction)
            openings.setdefault(nxt, set()).add(back)

        def center(cell):
            c, r = cell
            return (
                margin_x + c * MAZE_CELL + MAZE_CELL / 2,
                margin_y + r * MAZE_CELL + MAZE_CELL / 2,
            )

        self.floor_points = [center((c, r)) for r in range(MAZE_ROWS) for c in range(MAZE_COLS)]
        self.spawn_point = center(start)
        self.extract_point = center((MAZE_COLS - 1, MAZE_ROWS // 2))

        def add_wall(x, y, w, h):
            self.obstacles.append({
                "x": round(x, 1),
                "y": round(y, 1),
                "w": round(w, 1),
                "h": round(h, 1),
            })

        wall = MAZE_WALL
        total_w = MAZE_COLS * MAZE_CELL
        total_h = MAZE_ROWS * MAZE_CELL
        add_wall(margin_x - wall, margin_y - wall, total_w + wall * 2, wall)
        add_wall(margin_x - wall, margin_y + total_h, total_w + wall * 2, wall)
        add_wall(margin_x - wall, margin_y - wall, wall, total_h + wall * 2)
        add_wall(margin_x + total_w, margin_y - wall, wall, total_h + wall * 2)

        for r in range(MAZE_ROWS):
            for c in range(MAZE_COLS):
                cell = (c, r)
                x = margin_x + c * MAZE_CELL
                y = margin_y + r * MAZE_CELL
                cell_openings = openings.get(cell, set())
                if c < MAZE_COLS - 1 and "E" not in cell_openings:
                    add_wall(x + MAZE_CELL - wall / 2, y - wall / 2, wall, MAZE_CELL + wall)
                if r < MAZE_ROWS - 1 and "S" not in cell_openings:
                    add_wall(x - wall / 2, y + MAZE_CELL - wall / 2, MAZE_CELL + wall, wall)
        self._index_obstacles()

    def _jitter_floor_point(self, point, jitter=MAZE_SAFE_JITTER):
        x = point[0] + random.uniform(-jitter, jitter)
        y = point[1] + random.uniform(-jitter, jitter)
        return clamp(x, PLAYER_R, MAP_W - PLAYER_R), clamp(y, PLAYER_R, MAP_H - PLAYER_R)

    def _floor_spawn(self, min_player_dist=0, max_player_dist=None, near=None, far_from_spawn=False):
        points = self.floor_points or [(BASE_X, BASE_Y)]
        candidates = []
        for point in points:
            if far_from_spawn and math.hypot(point[0] - self.spawn_point[0], point[1] - self.spawn_point[1]) < MAZE_CELL * 2:
                continue
            if near is not None:
                d = math.hypot(point[0] - near["x"], point[1] - near["y"])
                if d < min_player_dist:
                    continue
                if max_player_dist is not None and d > max_player_dist:
                    continue
            elif min_player_dist:
                nearest = min((math.hypot(p["x"] - point[0], p["y"] - point[1]) for p in self.players.values()), default=9999)
                if nearest < min_player_dist:
                    continue
            candidates.append(point)
        if not candidates:
            candidates = points
        for _ in range(30):
            x, y = self._jitter_floor_point(random.choice(candidates))
            if any(circ_rect(x, y, PLAYER_R + 4, o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(x, y, PLAYER_R + MAZE_WALL + 4)):
                continue
            return x, y
        return self._jitter_floor_point(random.choice(candidates), jitter=20)

    def _build_grid(self, entities):
        grid = {}
        for eid, entity in entities.items():
            cx = int(entity["x"] // SPATIAL_CELL)
            cy = int(entity["y"] // SPATIAL_CELL)
            grid.setdefault((cx, cy), []).append((eid, entity))
        return grid

    def _index_obstacles(self):
        self.obstacle_grid = {}
        for idx, obstacle in enumerate(self.obstacles):
            c0x = math.floor(obstacle["x"] / SPATIAL_CELL)
            c1x = math.floor((obstacle["x"] + obstacle["w"]) / SPATIAL_CELL)
            c0y = math.floor(obstacle["y"] / SPATIAL_CELL)
            c1y = math.floor((obstacle["y"] + obstacle["h"]) / SPATIAL_CELL)
            for cy in range(c0y, c1y + 1):
                for cx in range(c0x, c1x + 1):
                    self.obstacle_grid.setdefault((cx, cy), []).append((idx, obstacle))

    def _near_obstacles(self, x, y, radius):
        if not self.obstacle_grid:
            yield from self.obstacles
            return
        c0x = math.floor((x - radius) / SPATIAL_CELL)
        c1x = math.floor((x + radius) / SPATIAL_CELL)
        c0y = math.floor((y - radius) / SPATIAL_CELL)
        c1y = math.floor((y + radius) / SPATIAL_CELL)
        seen = set()
        for cy in range(c0y, c1y + 1):
            for cx in range(c0x, c1x + 1):
                for idx, obstacle in self.obstacle_grid.get((cx, cy), ()):
                    if idx in seen:
                        continue
                    seen.add(idx)
                    yield obstacle

    def _near(self, grid, x, y, radius):
        c0x = math.floor((x - radius) / SPATIAL_CELL)
        c1x = math.floor((x + radius) / SPATIAL_CELL)
        c0y = math.floor((y - radius) / SPATIAL_CELL)
        c1y = math.floor((y + radius) / SPATIAL_CELL)
        seen = set()
        for cy in range(c0y, c1y + 1):
            for cx in range(c0x, c1x + 1):
                for eid, entity in grid.get((cx, cy), ()):
                    if eid in seen:
                        continue
                    seen.add(eid)
                    yield eid, entity

    def _zombies_near(self, grid, x, y, radius):
        return self._near(grid, x, y, radius)

    def move_col(self, x, y, radius, dx, dy):
        nx = max(radius, min(MAP_W - radius, x + dx))
        ny = max(radius, min(MAP_H - radius, y + dy))
        for obstacle in self._near_obstacles(nx, ny, radius + MAZE_WALL + 4):
            if circ_rect(nx, ny, radius, obstacle["x"], obstacle["y"], obstacle["w"], obstacle["h"]):
                if not circ_rect(nx, y, radius, obstacle["x"], obstacle["y"], obstacle["w"], obstacle["h"]):
                    ny = y
                elif not circ_rect(x, ny, radius, obstacle["x"], obstacle["y"], obstacle["w"], obstacle["h"]):
                    nx = x
                else:
                    nx, ny = x, y
        return nx, ny

    def safe_spawn(self):
        return self._floor_spawn(min_player_dist=190, far_from_spawn=True)

    def safe_player_spawn(self):
        return self._jitter_floor_point(self.spawn_point, jitter=70)

    def safe_zombie_spawn(self, pressure=False):
        alive = [p for p in self.players.values() if not p.get("dead")]
        if pressure and alive:
            target = random.choice(alive)
            return self._floor_spawn(
                min_player_dist=PRESSURE_SPAWN_MIN_DIST,
                max_player_dist=PRESSURE_SPAWN_MAX_DIST,
                near=target,
            )
        return self._floor_spawn(min_player_dist=430, far_from_spawn=True)

    def _zombie_type_for_wave(self):
        choices = []
        weights = []
        for ztype, meta in ZOMBIE_TYPES.items():
            if meta.get("weight", 0) <= 0:
                continue
            unlock = meta.get("unlock", 1)
            if self.wave < unlock:
                continue
            choices.append(ztype)
            growth = max(0, self.wave - unlock)
            weights.append(meta["weight"] + growth * (1 if ztype != "walker" else 0))
        return random.choices(choices, weights=weights)[0]

    def spawn_zombie(self, x=None, y=None, ztype=None, emit=True, pressure=False):
        if len(self.zombies) >= MAX_ZOMBIES:
            return None
        if x is None:
            x, y = self.safe_zombie_spawn(pressure=pressure)
        if ztype is None:
            ztype = self._zombie_type_for_wave()
        meta = ZOMBIE_TYPES[ztype]
        zid = self._next_z
        self._next_z += 1
        max_hp = int(meta["hp"] * (1 + min(0.55, (self.wave - 1) * 0.045)))
        self.zombies[zid] = {
            "id": zid,
            "x": x,
            "y": y,
            "vx": 0,
            "vy": 0,
            "type": ztype,
            "hp": max_hp,
            "max_hp": max_hp,
            "radius": meta["radius"],
            "color": meta["color"],
            "target": None,
            "leap_cd": 0,
            "scream_cd": 0,
            "rally_until": 0,
        }
        if emit:
            self._emit_near("z_spawn", self._zombie_event(zid, self.zombies[zid]), x, y)
        return zid

    def spawn_item(self, x=None, y=None, item_type=None, emit=True):
        if len(self.items) >= MAX_ITEMS:
            return None
        if x is None:
            x, y = self.safe_spawn()
        if any(pt_in_rect(x, y, o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(x, y, ITEM_R + MAZE_WALL)):
            return None
        if item_type is None:
            names = list(ITEM_TYPES.keys())
            weights = [ITEM_TYPES[name]["weight"] for name in names]
            item_type = random.choices(names, weights=weights)[0]
        meta = ITEM_TYPES[item_type]
        iid = self._next_i
        self._next_i += 1
        self.items[iid] = {
            "id": iid,
            "x": x,
            "y": y,
            "type": item_type,
            "color": meta["color"],
            "icon": meta["icon"],
            "name": meta["name"],
            "radius": ITEM_R,
        }
        if emit:
            self._emit("i_spawn", self._item_event(iid, self.items[iid]))
        return iid

    def _input_dir(self, keys):
        dx = (1 if keys.get("right") else 0) - (1 if keys.get("left") else 0)
        dy = (1 if keys.get("down") else 0) - (1 if keys.get("up") else 0)
        if dx and dy:
            inv = 1 / math.sqrt(2)
            dx *= inv
            dy *= inv
        return dx, dy

    def _player_protected(self, player, now):
        return now < player.get("protect_until", 0) or now < player.get("shield_until", 0)

    def _check_level_up(self, player):
        leveled = False
        while player.get("xp", 0) >= player.get("level", 1) * LEVEL_XP_BASE:
            player["xp"] -= player["level"] * LEVEL_XP_BASE
            player["level"] += 1
            player["max_hp"] = PLAYER_MAX_HP + min(45, (player["level"] - 1) * 5)
            player["hp"] = min(player["max_hp"], player.get("hp", player["max_hp"]) + 24)
            leveled = True
        return leveled

    def _gain_score(self, sid, amount, xp, now, x=None, y=None):
        player = self.players.get(sid)
        if not player or player.get("dead"):
            return
        player["score"] += amount
        player["kills"] += 1
        player["xp"] += xp
        if now < player.get("combo_until", 0):
            player["combo"] = player.get("combo", 0) + 1
        else:
            player["combo"] = 1
        player["combo_until"] = now + COMBO_WINDOW
        leveled = self._check_level_up(player)
        self._emit_to("score_gain", {
            "pid": sid,
            "score": player["score"],
            "kills": player["kills"],
            "combo": player["combo"],
            "x": round(x if x is not None else player["x"], 1),
            "y": round(y if y is not None else player["y"], 1),
            "col": player["color"],
            "level": player["level"],
        }, [sid])
        if leveled:
            self._emit("level_up", {
                "pid": sid,
                "level": player["level"],
                "x": round(player["x"], 1),
                "y": round(player["y"], 1),
                "col": player["color"],
            })
        self._maybe_combo_bonus(player, now)

    def _maybe_combo_bonus(self, player, now):
        combo = player.get("combo", 0)
        bonus = None
        if combo == COMBO_RAPID_BONUS_AT:
            player["rapid_until"] = max(player.get("rapid_until", 0), now + 4.5)
            bonus = {"type": "rapid", "name": "连杀速射"}
        elif combo == COMBO_SPREAD_BONUS_AT:
            player["spread_until"] = max(player.get("spread_until", 0), now + 5.0)
            bonus = {"type": "spread", "name": "连杀三连发"}
        elif combo == COMBO_SHIELD_BONUS_AT:
            player["shield_until"] = max(player.get("shield_until", 0), now + 5.0)
            bonus = {"type": "shield", "name": "连杀护盾"}
        if not bonus:
            return
        self._emit_to("combo_bonus", {
            "pid": player["id"],
            "combo": combo,
            "type": bonus["type"],
            "name": bonus["name"],
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "col": player["color"],
        }, [player["id"]])

    def _apply_item(self, sid, item, now):
        player = self.players.get(sid)
        if not player or player.get("dead"):
            return
        typ = item["type"]
        if ITEM_TYPES.get(typ, {}).get("task"):
            self.task_counts[typ] = self.task_counts.get(typ, 0) + 1
            self._emit("task_update", {
                "pid": sid,
                "type": typ,
                "name": item["name"],
                "count": self.task_counts[typ],
                "task": self._task_summary(),
                "x": round(item["x"], 1),
                "y": round(item["y"], 1),
                "col": item["color"],
            })
        elif typ == "rapid":
            player["rapid_until"] = now + 7.5
        elif typ == "spread":
            player["spread_until"] = now + 7.0
        elif typ == "shield":
            player["shield_until"] = now + 5.0
        elif typ == "medkit":
            player["hp"] = min(player["max_hp"], player.get("hp", player["max_hp"]) + 42)
        elif typ == "nuke":
            self._nuke(sid, item["x"], item["y"], now)
        self._emit_near("item_pick", {
            "pid": sid,
            "iid": item["id"],
            "type": typ,
            "name": item["name"],
            "icon": item["icon"],
            "col": item["color"],
            "x": round(item["x"], 1),
            "y": round(item["y"], 1),
        }, item["x"], item["y"], include=sid)

    def _nuke(self, sid, x, y, now):
        killed = 0
        for zid, zombie in list(self.zombies.items()):
            if math.hypot(zombie["x"] - x, zombie["y"] - y) <= NUKE_RADIUS:
                killed += 1
                self._kill_zombie(sid, zid, zombie, now, reason="nuke")
        self._emit_near(
            "nuke",
            {"pid": sid, "x": round(x, 1), "y": round(y, 1), "r": NUKE_RADIUS, "kills": killed},
            x,
            y,
            radius=NUKE_RADIUS + EVENT_INTEREST_RADIUS * 0.35,
            include=sid,
        )

    def _try_drop_item(self, x, y):
        if len(self.items) >= MAX_ITEMS:
            return
        if random.random() < 0.028:
            self.spawn_item(x, y)

    def _try_drop_task_item(self, zombie):
        if len(self.items) >= MAX_ITEMS:
            return
        ztype = zombie.get("type")
        item_type = None
        if ztype in ("toxic", "screamer", "bloater"):
            item_type = "sample" if random.random() < 0.78 else None
        elif ztype in ("runner", "brute", "armored", "boss"):
            item_type = "keycard" if random.random() < (0.55 if ztype != "runner" else 0.28) else None
        elif random.random() < TASK_DROP_CHANCE * 0.42:
            item_type = "sample"
        if item_type:
            self.spawn_item(zombie["x"], zombie["y"], item_type=item_type)

    def _collect_items(self, now):
        for iid, item in list(self.items.items()):
            for sid, player in self.players.items():
                if player.get("dead"):
                    continue
                if math.hypot(player["x"] - item["x"], player["y"] - item["y"]) <= PLAYER_R + item["radius"] + 8:
                    del self.items[iid]
                    self._apply_item(sid, item, now)
                    break

    def _expire_player_effects(self, now):
        for player in self.players.values():
            for field, typ in (("rapid_until", "rapid"), ("spread_until", "spread"), ("shield_until", "shield")):
                if player.get(field) and now > player.get(field, 0):
                    player[field] = 0
                    self._emit("item_end", {"pid": player["id"], "type": typ})

    def _try_shoot(self, sid, player, now):
        if player.get("dead") or not player.get("shooting"):
            return
        interval = FIRE_INTERVAL * (RAPID_FIRE_MULT if now < player.get("rapid_until", 0) else 1)
        if now < player.get("fire_cd", 0):
            return
        player["fire_cd"] = now + interval
        angles = [player.get("aim_angle", 0)]
        if now < player.get("spread_until", 0):
            angles = [angles[0] - SPREAD_ANGLE, angles[0], angles[0] + SPREAD_ANGLE]
        muzzle = PLAYER_R + 9
        for angle in angles:
            if len(self.bullets) >= MAX_BULLETS:
                break
            bid = self._next_b
            self._next_b += 1
            speed = BULLET_SPEED
            self.bullets[bid] = {
                "id": bid,
                "owner": sid,
                "x": player["x"] + math.cos(angle) * muzzle,
                "y": player["y"] + math.sin(angle) * muzzle,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "radius": BULLET_R,
                "life": BULLET_LIFE,
                "damage": BULLET_DAMAGE + max(0, player.get("level", 1) - 1) * 2 + min(18, (player.get("combo", 0) // 5) * 2),
                "color": player["color"],
            }

    def _update_bullets(self, dt, now):
        zombie_grid = self._build_grid(self.zombies)
        for bid, bullet in list(self.bullets.items()):
            bullet["life"] -= dt
            bullet["x"] += bullet["vx"] * dt
            bullet["y"] += bullet["vy"] * dt
            if bullet["life"] <= 0 or bullet["x"] < -40 or bullet["x"] > MAP_W + 40 or bullet["y"] < -40 or bullet["y"] > MAP_H + 40:
                self.bullets.pop(bid, None)
                continue
            if any(pt_in_rect(bullet["x"], bullet["y"], o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(bullet["x"], bullet["y"], bullet["radius"] + MAZE_WALL)):
                self.bullets.pop(bid, None)
                continue

            hit_id = None
            hit_zombie = None
            for zid, zombie in self._zombies_near(zombie_grid, bullet["x"], bullet["y"], bullet["radius"] + 34):
                if zid not in self.zombies:
                    continue
                if math.hypot(bullet["x"] - zombie["x"], bullet["y"] - zombie["y"]) <= bullet["radius"] + zombie["radius"]:
                    hit_id = zid
                    hit_zombie = zombie
                    break
            if hit_id is None:
                continue

            hit_zombie["hp"] -= bullet["damage"]
            hit_zombie["last_hit_by"] = bullet["owner"]
            self.bullets.pop(bid, None)
            if hit_zombie["hp"] <= 0:
                self._kill_zombie(bullet["owner"], hit_id, hit_zombie, now, reason="bullet")

    def _kill_zombie(self, sid, zid, zombie, now, reason="bullet"):
        if zid not in self.zombies:
            return
        self.zombies.pop(zid, None)
        meta = ZOMBIE_TYPES.get(zombie["type"], ZOMBIE_TYPES["walker"])
        self.wave_kills += 1
        self._gain_score(sid, meta["score"], max(8, meta["score"] // 2), now, zombie["x"], zombie["y"])
        self._emit_near("z_die", {
            "zid": zid,
            "pid": sid,
            "type": zombie["type"],
            "x": round(zombie["x"], 1),
            "y": round(zombie["y"], 1),
            "col": meta["color"],
            "reason": reason,
        }, zombie["x"], zombie["y"], include=sid)
        if zombie["type"] == "bloater":
            self._explode_bloater(sid, zid, zombie, now)
        self._try_drop_task_item(zombie)
        self._try_drop_item(zombie["x"], zombie["y"])

    def _explode_bloater(self, sid, zid, zombie, now):
        x = zombie["x"]
        y = zombie["y"]
        self._emit_near("z_explode", {
            "zid": zid,
            "pid": sid,
            "x": round(x, 1),
            "y": round(y, 1),
            "r": BLOATER_RADIUS,
            "col": ZOMBIE_TYPES["bloater"]["color"],
        }, x, y, radius=BLOATER_RADIUS + EVENT_INTEREST_RADIUS * 0.5, include=sid)

        for psid, player in list(self.players.items()):
            if math.hypot(player["x"] - x, player["y"] - y) <= BLOATER_RADIUS + PLAYER_R:
                self._damage_player(psid, BLOATER_PLAYER_DAMAGE, now, source=f"bloater:{zid}")

        for other_id, other in list(self.zombies.items()):
            if other_id not in self.zombies:
                continue
            if math.hypot(other["x"] - x, other["y"] - y) > BLOATER_RADIUS + other.get("radius", 16):
                continue
            other["hp"] -= BLOATER_ZOMBIE_DAMAGE
            other["last_hit_by"] = sid
            if other["hp"] <= 0:
                self._kill_zombie(sid, other_id, other, now, reason="blast")

    def _damage_player(self, sid, amount, now, source=None):
        player = self.players.get(sid)
        if not player or player.get("dead") or self._player_protected(player, now):
            return
        player["hp"] -= amount
        if player["hp"] <= 0:
            self._kill_player(sid, source or "zombie", now)

    def _kill_player(self, sid, killer, now):
        player = self.players.get(sid)
        if not player or player.get("dead"):
            return
        player["dead"] = True
        player["death_time"] = now
        player["hp"] = 0
        player["vx"] = 0
        player["vy"] = 0
        player["shooting"] = False
        self._emit("p_die", {
            "pid": sid,
            "killer": killer,
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "col": player["color"],
        })

    def _try_dash(self, sid, player, now):
        if player.get("dead") or now < player.get("dash_cd", 0):
            return
        dx, dy = self._input_dir(player.get("keys", {}))
        if not dx and not dy:
            dx = math.cos(player.get("aim_angle", 0))
            dy = math.sin(player.get("aim_angle", 0))
        sx, sy = player["x"], player["y"]
        player["x"], player["y"] = self.move_col(player["x"], player["y"], PLAYER_R, dx * DASH_DIST, dy * DASH_DIST)
        player["vx"] = dx * player_speed(player.get("level", 1)) * 0.22
        player["vy"] = dy * player_speed(player.get("level", 1)) * 0.22
        player["dash_cd"] = now + DASH_CD
        self._emit_near("p_dash", {
            "pid": sid,
            "sx": round(sx, 1),
            "sy": round(sy, 1),
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "cd": DASH_CD,
            "col": player["color"],
        }, player["x"], player["y"], include=sid)

    def _update_players(self, dt, now):
        for sid, player in list(self.players.items()):
            if player.get("combo") and now > player.get("combo_until", 0):
                player["combo"] = 0
            if player.get("dead"):
                player["vx"] = 0
                player["vy"] = 0
                continue

            dx, dy = self._input_dir(player.get("keys", {}))
            speed = player_speed(player.get("level", 1))
            target_vx = dx * speed
            target_vy = dy * speed
            rate = MOVE_ACCEL if (dx or dy) else MOVE_DECEL
            player["vx"] = approach(player.get("vx", 0), target_vx, rate * dt)
            player["vy"] = approach(player.get("vy", 0), target_vy, rate * dt)
            if abs(player["vx"]) < 0.01:
                player["vx"] = 0
            if abs(player["vy"]) < 0.01:
                player["vy"] = 0
            if player["vx"] or player["vy"]:
                player["x"], player["y"] = self.move_col(player["x"], player["y"], PLAYER_R, player["vx"] * dt, player["vy"] * dt)
            self._try_shoot(sid, player, now)

    def _zombie_target(self, zombie, alive, now):
        candidates = []
        for player in alive:
            d2 = (player["x"] - zombie["x"]) ** 2 + (player["y"] - zombie["y"]) ** 2
            candidates.append((d2, {
                "id": player["id"],
                "kind": "player",
                "x": player["x"],
                "y": player["y"],
                "radius": PLAYER_R,
            }))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]

    def _steer_zombie(self, zombie, target, speed, dt):
        dx = target["x"] - zombie["x"]
        dy = target["y"] - zombie["y"]
        dist = math.hypot(dx, dy)
        if dist <= 0.01 or speed <= 0:
            return 0, 0, zombie["x"], zombie["y"], dist
        base_angle = math.atan2(dy, dx)
        step = speed * dt
        direct_vx = math.cos(base_angle) * speed
        direct_vy = math.sin(base_angle) * speed
        direct_x, direct_y = self.move_col(zombie["x"], zombie["y"], zombie["radius"], direct_vx * dt, direct_vy * dt)
        direct_moved = math.hypot(direct_x - zombie["x"], direct_y - zombie["y"])
        direct_d2 = (target["x"] - direct_x) ** 2 + (target["y"] - direct_y) ** 2
        blocked = direct_moved < step * 0.72 or direct_d2 >= dist * dist - step * 0.45
        if not blocked:
            zombie["avoid_side"] = 0
            zombie["stuck_for"] = 0
            return direct_vx, direct_vy, direct_x, direct_y, dist

        side = zombie.get("avoid_side") or (1 if zombie.get("id", 0) % 2 else -1)
        zombie["avoid_side"] = side
        offsets = (side * 1.35, side * 1.57, side * 1.08, side * 0.74, side * 2.05, -side * 1.57, -side * 1.08, 0)
        best = None
        for rank, offset in enumerate(offsets):
            angle = base_angle + offset
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            nx, ny = self.move_col(zombie["x"], zombie["y"], zombie["radius"], vx * dt, vy * dt)
            moved = math.hypot(nx - zombie["x"], ny - zombie["y"])
            if moved < min(ZOMBIE_STUCK_EPS, step * 0.35):
                continue
            next_d2 = (target["x"] - nx) ** 2 + (target["y"] - ny) ** 2
            score = next_d2 * 0.24 + rank * 55 - moved * 260
            if best is None or score < best[0]:
                best = (score, vx, vy, nx, ny, moved)
        if best is None:
            sidestep = base_angle + random.choice((-1, 1)) * math.pi / 2
            vx = math.cos(sidestep) * speed * 0.58
            vy = math.sin(sidestep) * speed * 0.58
            nx, ny = self.move_col(zombie["x"], zombie["y"], zombie["radius"], vx * dt, vy * dt)
            return vx, vy, nx, ny, dist
        _, vx, vy, nx, ny, moved = best
        zombie["stuck_for"] = 0 if moved >= step * 0.48 else zombie.get("stuck_for", 0) + dt
        if zombie.get("stuck_for", 0) > ZOMBIE_STUCK_AFTER:
            zombie["avoid_side"] = -zombie.get("avoid_side", 1) or -1
            zombie["stuck_for"] = 0
        return vx, vy, nx, ny, dist

    def _maybe_scream(self, zid, zombie, now):
        if zombie["type"] != "screamer" or now < zombie.get("scream_cd", 0):
            return
        zombie["scream_cd"] = now + SCREAMER_COOLDOWN
        rallied = 0
        for other_id, other in self.zombies.items():
            if other_id == zid:
                continue
            if math.hypot(other["x"] - zombie["x"], other["y"] - zombie["y"]) > SCREAMER_RADIUS + other.get("radius", 16):
                continue
            other["rally_until"] = max(other.get("rally_until", 0), now + SCREAMER_RALLY_SECONDS)
            rallied += 1
        self._emit_near("z_scream", {
            "zid": zid,
            "x": round(zombie["x"], 1),
            "y": round(zombie["y"], 1),
            "r": SCREAMER_RADIUS,
            "buffed": rallied,
            "col": ZOMBIE_TYPES["screamer"]["color"],
        }, zombie["x"], zombie["y"])

    def _maybe_leap_speed(self, zombie, target, speed, dist, now):
        if zombie["type"] != "leaper":
            return speed
        if dist < LEAPER_MIN_RANGE or dist > LEAPER_MAX_RANGE or now < zombie.get("leap_cd", 0):
            return speed
        zombie["leap_cd"] = now + LEAPER_COOLDOWN
        self._emit_near("z_leap", {
            "zid": zombie["id"],
            "sx": round(zombie["x"], 1),
            "sy": round(zombie["y"], 1),
            "x": round(target["x"], 1),
            "y": round(target["y"], 1),
            "col": ZOMBIE_TYPES["leaper"]["color"],
        }, zombie["x"], zombie["y"])
        return speed * LEAPER_SPEED_MULT

    def _damage_base(self, amount, now, source=None):
        return

    def _maintain_base(self, now):
        return

    def _advance_stage(self, now, exit_point, players_in_zone):
        cleared_stage = self.wave
        self._emit("wave_clear", {
            "wave": cleared_stage,
            "name": exit_point["name"],
            "x": round(exit_point["x"], 1),
            "y": round(exit_point["y"], 1),
        })
        self.wave += 1
        self.wave_remaining = self._wave_budget()
        self.wave_kills = 0
        self.wave_announced = True
        self.zombies.clear()
        self.bullets.clear()
        self.items.clear()
        self._gen_obstacles()
        self._start_stage_tasks()
        for sid, player in self.players.items():
            sx, sy = self.safe_player_spawn()
            player["x"] = sx
            player["y"] = sy
            player["vx"] = 0
            player["vy"] = 0
            player["dead"] = False
            player["hp"] = min(player["max_hp"], max(player.get("hp", player["max_hp"]), player["max_hp"] * 0.72))
            player["protect_until"] = now + PROTECT
            self._emit("p_resp", {"pid": sid, "x": sx, "y": sy, "hp": round(player["hp"], 1)})
        stage_zombies = min(INITIAL_ZOMBIES + self.wave * 3, self.wave_remaining)
        for _ in range(stage_zombies):
            if self.spawn_zombie(emit=False, pressure=True):
                self.wave_remaining -= 1
        for _ in range(INITIAL_ITEMS):
            self.spawn_item(emit=False)
        self._emit("wave_start", {
            "wave": self.wave,
            "remaining": self.wave_remaining,
            "boss": self._is_boss_wave(),
            "story": self._story_for_wave(),
            "obj": self._objective_snapshot(),
            "mission": self._mission_snapshot(),
            "exits": self._extractions_snapshot(),
            "obs": self.obstacles,
            "base": None,
        })

    def _complete_mission(self, now, exit_point, players_in_zone):
        if not exit_point or exit_point.get("done"):
            return
        exit_point["done"] = True
        exit_point["charge"] = 1.0
        for sid in players_in_zone:
            player = self.players.get(sid)
            if not player or player.get("dead"):
                continue
            player["score"] += MISSION_REWARD_SCORE
            player["xp"] += MISSION_REWARD_XP
            player["shield_until"] = max(player.get("shield_until", 0), now + 3.5)
            if self.wave % 3 == 0:
                player["rapid_until"] = max(player.get("rapid_until", 0), now + 4.0)
            if self._check_level_up(player):
                self._emit("level_up", {
                    "pid": sid,
                    "level": player["level"],
                    "x": round(player["x"], 1),
                    "y": round(player["y"], 1),
                    "col": player["color"],
                })
        self._emit("mission_complete", {
            "name": exit_point["name"],
            "x": round(exit_point["x"], 1),
            "y": round(exit_point["y"], 1),
            "players": len(players_in_zone),
            "wave": self.wave,
            "nextWave": self.wave + 1,
        })
        self._advance_stage(now, exit_point, players_in_zone)

    def _update_mission(self, dt, now):
        if not self.extractions:
            return
        alive_players = [(sid, player) for sid, player in self.players.items() if not player.get("dead")]
        for exit_point in self.extractions:
            if exit_point.get("done"):
                continue
            nearby = [
                sid for sid, player in alive_players
                if math.hypot(player["x"] - exit_point["x"], player["y"] - exit_point["y"]) <= EXTRACTION_DISCOVER_RADIUS
            ]
            if nearby and not exit_point.get("visible"):
                exit_point["visible"] = True
                self.mission = exit_point
                self._emit_near("mission_revealed", {
                    "id": exit_point["id"],
                    "name": exit_point["name"],
                    "text": exit_point["text"],
                    "requires": exit_point["requires"],
                    "requireText": self._requires_text(exit_point["requires"]),
                    "x": round(exit_point["x"], 1),
                    "y": round(exit_point["y"], 1),
                    "col": exit_point["color"],
                }, exit_point["x"], exit_point["y"])

            players_in_zone = [
                sid for sid, player in alive_players
                if math.hypot(player["x"] - exit_point["x"], player["y"] - exit_point["y"]) <= exit_point["radius"] + PLAYER_R
            ]
            if players_in_zone and self._exit_ready(exit_point):
                exit_point["visible"] = True
                self.mission = exit_point
                exit_point["charge"] = min(1.0, exit_point.get("charge", 0) + dt * len(players_in_zone) / EXTRACTION_CAPTURE_SECONDS)
            else:
                exit_point["charge"] = max(0, exit_point.get("charge", 0) - dt * 0.08)
            if exit_point["charge"] >= 1:
                self._complete_mission(now, exit_point, players_in_zone)
                return

    def _update_zombies(self, dt, now):
        alive = [p for p in self.players.values() if not p.get("dead")]
        if not alive:
            return
        for zid, zombie in list(self.zombies.items()):
            target = self._zombie_target(zombie, alive, now)
            if not target:
                continue
            speed = zombie_speed(zombie["type"], self.wave)
            if now < zombie.get("rally_until", 0):
                speed *= SCREAMER_RALLY_MULT
            self._maybe_scream(zid, zombie, now)
            dx = target["x"] - zombie["x"]
            dy = target["y"] - zombie["y"]
            speed = self._maybe_leap_speed(zombie, target, speed, math.hypot(dx, dy), now)
            vx, vy, nx, ny, dist = self._steer_zombie(zombie, target, speed, dt)
            zombie["target"] = target["id"]
            zombie["vx"] = vx
            zombie["vy"] = vy
            zombie["x"], zombie["y"] = nx, ny
            dist_after = math.hypot(target["x"] - zombie["x"], target["y"] - zombie["y"])
            if dist_after <= zombie["radius"] + target["radius"] + 8:
                meta = ZOMBIE_TYPES.get(zombie["type"], ZOMBIE_TYPES["walker"])
                self._damage_player(target["id"], meta["damage"] * dt, now, zid)

    def _director_pressure(self, dt, now):
        self.director_timer += dt
        if self.director_timer < DIRECTOR_CHECK_DT:
            return
        self.director_timer = 0.0
        alive = [p for p in self.players.values() if not p.get("dead")]
        watch_points = alive[:]
        if not watch_points or not self.zombies:
            return

        leash_sq = DIRECTOR_LEASH_RADIUS * DIRECTOR_LEASH_RADIUS
        near_sq = ZOMBIE_INTEREST_RADIUS * ZOMBIE_INTEREST_RADIUS
        near_count = 0
        relocated = 0
        for zid, zombie in list(self.zombies.items()):
            min_d2 = min((point["x"] - zombie["x"]) ** 2 + (point["y"] - zombie["y"]) ** 2 for point in watch_points)
            if min_d2 <= near_sq:
                near_count += 1
            if min_d2 <= leash_sq:
                zombie["far_since"] = 0
                continue
            far_since = zombie.get("far_since") or now
            zombie["far_since"] = far_since
            if now - far_since < DIRECTOR_LEASH_AFTER:
                continue
            x, y = self.safe_zombie_spawn(pressure=True)
            zombie["x"] = x
            zombie["y"] = y
            zombie["vx"] = 0
            zombie["vy"] = 0
            zombie["target"] = None
            zombie["far_since"] = 0
            relocated += 1
            self._emit_near("z_spawn", self._zombie_event(zid, zombie), x, y)
            if relocated >= DIRECTOR_MAX_PRESSURE_SPAWNS:
                break

        if self.wave_remaining <= 0 or len(self.zombies) >= MAX_ZOMBIES:
            return
        desired = min(
            DIRECTOR_MAX_NEAR_ZOMBIES,
            max(DIRECTOR_MIN_NEAR_ZOMBIES, max(1, len(alive)) * DIRECTOR_NEAR_ZOMBIES_PER_PLAYER),
        )
        deficit = desired - near_count
        if deficit <= 0:
            return
        budget = min(
            deficit,
            DIRECTOR_MAX_PRESSURE_SPAWNS,
            self.wave_remaining,
            MAX_ZOMBIES - len(self.zombies),
        )
        for _ in range(max(0, budget)):
            if self.spawn_zombie(pressure=True):
                self.wave_remaining -= 1

    def _spawn_wave_burst(self):
        alive_count = max(1, sum(1 for player in self.players.values() if not player.get("dead")))
        budget = min(
            WAVE_BURST_MAX,
            WAVE_BURST_BASE + alive_count * WAVE_BURST_PER_PLAYER + self.wave * 2,
            self.wave_remaining,
            MAX_ZOMBIES - len(self.zombies),
        )
        scripted = (
            ("brute", 2),
            ("toxic", 3),
            ("crawler", 2),
            ("armored", 4),
            ("leaper", 5),
            ("screamer", 6),
            ("bloater", 7),
        )
        scripted_offset = 1 if self._is_boss_wave() else 0
        for i in range(max(0, budget)):
            ztype = None
            if self._is_boss_wave() and i == 0:
                ztype = "boss"
            else:
                slot = i - scripted_offset
                if 0 <= slot < len(scripted):
                    candidate, unlock = scripted[slot]
                    if self.wave >= unlock:
                        ztype = candidate
            zid = self.spawn_zombie(ztype=ztype, pressure=True)
            if zid:
                self.wave_remaining -= 1
                if ztype == "boss":
                    zombie = self.zombies[zid]
                    self._emit("boss_spawn", {
                        "id": zid,
                        "wave": self.wave,
                        "name": "黑墙巨像",
                        "x": round(zombie["x"], 1),
                        "y": round(zombie["y"], 1),
                        "hp": zombie["hp"],
                        "maxHp": zombie["max_hp"],
                        "color": zombie["color"],
                    })

    def _reward_wave_clear(self, now, cleared_wave):
        repair = BASE_REPAIR_PER_WAVE + sum(1 for player in self.players.values() if not player.get("dead")) * BASE_REPAIR_PER_PLAYER
        self._repair_base(repair, now, reason="wave")
        for sid, player in self.players.items():
            if player.get("dead"):
                continue
            player["hp"] = min(player["max_hp"], player.get("hp", player["max_hp"]) + 26)
            player["shield_until"] = max(player.get("shield_until", 0), now + 3.2)
            if cleared_wave % 2 == 0:
                self.spawn_item(
                    clamp(player["x"] + random.uniform(-180, 180), ITEM_R, MAP_W - ITEM_R),
                    clamp(player["y"] + random.uniform(-180, 180), ITEM_R, MAP_H - ITEM_R),
                )
            self._emit_to("wave_reward", {
                "pid": sid,
                "wave": cleared_wave,
                "hp": round(player["hp"], 1),
                "x": round(player["x"], 1),
                "y": round(player["y"], 1),
                "col": player["color"],
            }, [sid])

    def _maintain_zombies(self, dt, now):
        if self.wave_remaining <= 0 or len(self.zombies) >= MAX_ZOMBIES:
            return
        self.zombie_spawn_timer += dt
        if self.zombie_spawn_timer < ZOMBIE_SPAWN_DT:
            return
        self.zombie_spawn_timer = 0.0
        budget = min(5, self.wave_remaining, MAX_ZOMBIES - len(self.zombies))
        for _ in range(max(0, budget)):
            if self.spawn_zombie(pressure=self.wave >= 2 and random.random() < 0.55):
                self.wave_remaining -= 1

    def _maintain_items(self, dt):
        self.item_spawn_timer += dt
        if self.item_spawn_timer < ITEM_SPAWN_DT:
            return
        self.item_spawn_timer = 0.0
        if len(self.items) < max(4, MAX_ITEMS // 2):
            self.spawn_item()

    def _drop_stale_inputs(self, now):
        for player in self.players.values():
            if now - player.get("last_input", now) > INPUT_IDLE_TIMEOUT:
                player["keys"] = {}
                player["shooting"] = False
                player["vx"] = 0
                player["vy"] = 0

    def _remove_stale_players(self, now):
        for sid, player in list(self.players.items()):
            if now - player.get("last_seen", player.get("last_input", now)) > PLAYER_STALE_TIMEOUT:
                self.remove_player(sid)
                self._emit("p_leave", {"pid": sid, "reason": "timeout"})

    def tick(self, dt=SERVER_DT, now=None):
        perf_start = time.perf_counter()
        try:
            now = self._now() if now is None else now
            dt = clamp(finite_float(dt, SERVER_DT), 0.0, 0.05)
            self.last_tick = now
            if not self.running or not self.players:
                return
            self.tick_id += 1
            self._drop_stale_inputs(now)
            self._remove_stale_players(now)
            self._maintain_zombies(dt, now)
            self._director_pressure(dt, now)
            self._maintain_items(dt)
            self._expire_player_effects(now)
            self._update_players(dt, now)
            self._update_mission(dt, now)
            self._maintain_base(now)
            self._update_zombies(dt, now)
            self._update_bullets(dt, now)
            self._collect_items(now)
            self._maintain_base(now)

            for pid, player in self.players.items():
                if player.get("dead") and now - player.get("death_time", now) > 2.3:
                    sx, sy = self.safe_player_spawn()
                    player["x"] = sx
                    player["y"] = sy
                    player["vx"] = 0
                    player["vy"] = 0
                    player["hp"] = player["max_hp"]
                    player["dead"] = False
                    player["protect_until"] = now + PROTECT
                    self._emit("p_resp", {"pid": pid, "x": sx, "y": sy, "hp": player["hp"]})
        finally:
            self._record_tick_perf(perf_start)

    def add_player(self, sid):
        if sid in self.players:
            player = self.players[sid]
            now = self._now()
            player["last_input"] = now
            player["last_seen"] = now
            return player["idx"], player["x"], player["y"]
        used = {p["idx"] for p in self.players.values()}
        idx = 0
        while idx in used:
            idx += 1
        sx, sy = self.safe_player_spawn()
        now = self._now()
        self.players[sid] = {
            "id": sid,
            "x": sx,
            "y": sy,
            "hp": PLAYER_MAX_HP,
            "max_hp": PLAYER_MAX_HP,
            "color": player_color(idx),
            "name": player_name(idx),
            "score": 0,
            "kills": 0,
            "dead": False,
            "death_time": 0,
            "vx": 0,
            "vy": 0,
            "aim_angle": 0,
            "shooting": False,
            "fire_cd": 0,
            "rapid_until": 0,
            "spread_until": 0,
            "shield_until": 0,
            "dash_cd": 0,
            "level": 1,
            "xp": 0,
            "combo": 0,
            "combo_until": 0,
            "input_seq": 0,
            "ack_seq": 0,
            "idx": idx,
            "keys": {},
            "protect_until": now + PROTECT,
            "last_input": now,
            "last_seen": now,
        }
        return idx, sx, sy

    def remove_player(self, sid):
        removed = sid in self.players
        if removed:
            del self.players[sid]
            for bid, bullet in list(self.bullets.items()):
                if bullet.get("owner") == sid:
                    self.bullets.pop(bid, None)
        if not self.players:
            self.running = False
        return removed

    def handle_input(self, sid, data):
        player = self.players.get(sid)
        if not player:
            return
        inp = normalize_input(data)
        if inp["seq"] < player.get("input_seq", 0):
            return
        now = self._now()
        player["input_seq"] = inp["seq"]
        player["ack_seq"] = inp["seq"]
        player["keys"] = inp["keys"]
        player["aim_angle"] = inp["aim_angle"]
        player["shooting"] = inp["shooting"]
        player["last_input"] = now
        player["last_seen"] = now
        if inp["dash"]:
            self._try_dash(sid, player, now)
        self._try_shoot(sid, player, now)

    def mark_seen(self, sid, now=None):
        player = self.players.get(sid)
        if not player:
            return False
        player["last_seen"] = self._now() if now is None else now
        return True

    def _player_tuple(self, player, now):
        max_hp = player.get("max_hp", PLAYER_MAX_HP)
        hp = clamp(player.get("hp", max_hp), 0, max_hp)
        player["hp"] = hp
        return [
            round(player["x"], 1),
            round(player["y"], 1),
            round(hp, 1),
            player["score"],
            player["dead"],
            now < player.get("rapid_until", 0),
            round(player.get("aim_angle", 0), 2),
            self._player_protected(player, now),
            player["color"],
            player["name"],
            player.get("level", 1),
            player.get("combo", 0) if now < player.get("combo_until", 0) else 0,
            round(max(0, player.get("fire_cd", 0) - now), 2),
            player.get("xp", 0),
            player.get("ack_seq", 0),
            round(player.get("vx", 0), 1),
            round(player.get("vy", 0), 1),
            PLAYER_R,
            round(player_speed(player.get("level", 1)), 1),
            player.get("kills", 0),
            now < player.get("spread_until", 0),
            max_hp,
        ]

    def _zombie_tuple(self, zombie):
        return [
            round(zombie["x"], 1),
            round(zombie["y"], 1),
            round(max(0, zombie["hp"]), 1),
            zombie["type"],
            zombie["color"],
            zombie["radius"],
            zombie.get("target"),
            round(zombie.get("vx", 0), 1),
            round(zombie.get("vy", 0), 1),
            zombie.get("max_hp", zombie["hp"]),
        ]

    def _bullet_tuple(self, bullet):
        return [
            round(bullet["x"], 1),
            round(bullet["y"], 1),
            round(bullet["vx"], 1),
            round(bullet["vy"], 1),
            bullet["color"],
            bullet["radius"],
            bullet["owner"],
            round(max(0, bullet["life"]), 2),
        ]

    def _item_tuple(self, item):
        return [
            round(item["x"], 1),
            round(item["y"], 1),
            item["type"],
            item["color"],
            item["icon"],
            item["name"],
            item["radius"],
        ]

    def _zombie_event(self, zid, zombie):
        return {
            "id": zid,
            "x": round(zombie["x"], 1),
            "y": round(zombie["y"], 1),
            "hp": zombie["hp"],
            "maxHp": zombie["max_hp"],
            "type": zombie["type"],
            "color": zombie["color"],
            "radius": zombie["radius"],
        }

    def _item_event(self, iid, item):
        return {
            "id": iid,
            "x": round(item["x"], 1),
            "y": round(item["y"], 1),
            "type": item["type"],
            "color": item["color"],
            "icon": item["icon"],
            "name": item["name"],
            "radius": item["radius"],
        }

    def _near_player_tuples(self, sid, viewer, player_tuples):
        candidates = []
        radius_sq = PLAYER_INTEREST_RADIUS * PLAYER_INTEREST_RADIUS
        for pid, player in self.players.items():
            if pid == sid:
                candidates.append((0.0, pid))
                continue
            d2 = (player["x"] - viewer["x"]) ** 2 + (player["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((d2, pid))
        if len(candidates) > MAX_SYNC_PLAYERS_PER_CLIENT:
            candidates.sort(key=lambda item: item[0])
            candidates = candidates[:MAX_SYNC_PLAYERS_PER_CLIENT]
        return {pid: player_tuples[pid] for _, pid in candidates if pid in player_tuples}

    def _limited_zombies_near(self, grid, viewer):
        radius_sq = ZOMBIE_INTEREST_RADIUS * ZOMBIE_INTEREST_RADIUS
        candidates = []
        for zid, zombie in self._zombies_near(grid, viewer["x"], viewer["y"], ZOMBIE_INTEREST_RADIUS):
            d2 = (zombie["x"] - viewer["x"]) ** 2 + (zombie["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((d2, zid, zombie))
        if len(candidates) > MAX_SYNC_ZOMBIES_PER_CLIENT:
            candidates.sort(key=lambda item: item[0])
            candidates = candidates[:MAX_SYNC_ZOMBIES_PER_CLIENT]
        return {zid: self._zombie_tuple(zombie) for _, zid, zombie in candidates}

    def _limited_bullets_near(self, viewer):
        radius_sq = BULLET_INTEREST_RADIUS * BULLET_INTEREST_RADIUS
        candidates = []
        for bid, bullet in self.bullets.items():
            d2 = (bullet["x"] - viewer["x"]) ** 2 + (bullet["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((d2, bid, bullet))
        if len(candidates) > MAX_SYNC_BULLETS_PER_CLIENT:
            candidates.sort(key=lambda item: item[0])
            candidates = candidates[:MAX_SYNC_BULLETS_PER_CLIENT]
        return {bid: self._bullet_tuple(bullet) for _, bid, bullet in candidates}

    def _limited_items_near(self, viewer):
        radius_sq = ITEM_INTEREST_RADIUS * ITEM_INTEREST_RADIUS
        candidates = []
        for iid, item in self.items.items():
            d2 = (item["x"] - viewer["x"]) ** 2 + (item["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((d2, iid, item))
        if len(candidates) > MAX_SYNC_ITEMS_PER_CLIENT:
            candidates.sort(key=lambda item: item[0])
            candidates = candidates[:MAX_SYNC_ITEMS_PER_CLIENT]
        return {iid: self._item_tuple(item) for _, iid, item in candidates}

    def _leaderboard(self):
        rows = sorted(
            self.players.values(),
            key=lambda player: (player.get("score", 0), player.get("kills", 0)),
            reverse=True,
        )[:LEADERBOARD_SIZE]
        return [
            {
                "name": player.get("name", "幸存者"),
                "color": player.get("color", "#ffffff"),
                "score": player.get("score", 0),
                "kills": player.get("kills", 0),
                "level": player.get("level", 1),
                "dead": bool(player.get("dead")),
            }
            for player in rows
        ]

    def _snapshot_payload(self, sid, now, player_tuples, zombie_grid, leaderboard):
        if sid and sid in self.players:
            viewer = self.players[sid]
            players = self._near_player_tuples(sid, viewer, player_tuples)
            zombies = self._limited_zombies_near(zombie_grid, viewer)
            bullets = self._limited_bullets_near(viewer)
            items = self._limited_items_near(viewer)
        else:
            players = player_tuples
            zombies = {zid: self._zombie_tuple(zombie) for zid, zombie in self.zombies.items()}
            bullets = {bid: self._bullet_tuple(bullet) for bid, bullet in self.bullets.items()}
            items = {iid: self._item_tuple(item) for iid, item in self.items.items()}
        return {
            "v": PROTOCOL_VERSION,
            "tick": self.tick_id,
            "time": round(now, 3),
            "p": players,
            "z": zombies,
            "b": bullets,
            "i": items,
            "zt": len(self.zombies),
            "bt": len(self.bullets),
            "it": len(self.items),
            "w": self.wave,
            "wr": self.wave_remaining,
            "wa": self.wave_announced,
            "lb": leaderboard,
            "obj": self._objective_snapshot(full=False),
            "base": self._base_snapshot(now),
            "mission": self._mission_snapshot(full=False),
            "exits": self._extractions_snapshot(full=False),
        }

    def get_snapshot(self, sid=None, zombie_grid=None):
        perf_start = time.perf_counter()
        now = self._now()
        player_tuples = {pid: self._player_tuple(player, now) for pid, player in self.players.items()}
        snap = self._snapshot_payload(
            sid,
            now,
            player_tuples,
            zombie_grid or self._build_grid(self.zombies),
            self._leaderboard(),
        )
        self._record_snapshot_perf(perf_start)
        snap["perf"] = self._perf_snapshot()
        return snap

    def get_snapshots_by_player(self):
        perf_start = time.perf_counter()
        now = self._now()
        player_tuples = {pid: self._player_tuple(player, now) for pid, player in self.players.items()}
        grid = self._build_grid(self.zombies)
        leaderboard = self._leaderboard()
        packets = []
        for pid in list(self.players.keys()):
            snap = self._snapshot_payload(pid, now, player_tuples, grid, leaderboard)
            packets.append((pid, snap))
        self._record_snapshot_perf(perf_start)
        perf = self._perf_snapshot()
        for _, snap in packets:
            snap["perf"] = perf
        return packets

    def get_init_data(self, sid, idx):
        now = self._now()
        return {
            "v": PROTOCOL_VERSION,
            "tick": self.tick_id,
            "time": round(now, 3),
            "id": sid,
            "col": player_color(idx),
            "nm": player_name(idx),
            "idx": idx,
            "cfg": {
                "playerSpeed": PLAYER_SPD,
                "playerRadius": PLAYER_R,
                "playerMaxHp": PLAYER_MAX_HP,
                "dashDist": DASH_DIST,
                "dashCd": DASH_CD,
                "fireInterval": FIRE_INTERVAL,
                "bulletSpeed": BULLET_SPEED,
                "moveAccel": MOVE_ACCEL,
                "moveDecel": MOVE_DECEL,
                "serverTickHz": SERVER_TICK_HZ,
                "snapshotHz": SNAPSHOT_HZ,
            },
            "mw": MAP_W,
            "mh": MAP_H,
            "obs": self.obstacles,
            "z": {zid: self._zombie_tuple(zombie) for zid, zombie in self.zombies.items()},
            "b": {bid: self._bullet_tuple(bullet) for bid, bullet in self.bullets.items()},
            "i": {iid: self._item_tuple(item) for iid, item in self.items.items()},
            "pl": {pid: self._player_tuple(player, now) for pid, player in self.players.items()},
            "w": self.wave,
            "wr": self.wave_remaining,
            "lb": self._leaderboard(),
            "obj": self._objective_snapshot(),
            "base": self._base_snapshot(now),
            "mission": self._mission_snapshot(),
            "exits": self._extractions_snapshot(),
        }
