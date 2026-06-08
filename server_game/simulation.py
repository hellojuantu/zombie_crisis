"""Authoritative zombie shooter simulation."""

import heapq
import json
import math
import random
import time

from .config import (
    BULLET_DAMAGE,
    BULLET_LIFE,
    BULLET_R,
    BULLET_SPEED,
    CASE_FILES,
    BLOATER_PLAYER_DAMAGE,
    BLOATER_RADIUS,
    BLOATER_ZOMBIE_DAMAGE,
    BOSS_WAVE_INTERVAL,
    CAMPAIGN_FINAL_WAVE,
    AMMO_PICKUP_BY_TYPE,
    AMMO_PICKUP_MAX,
    AMMO_PICKUP_MIN,
    AMMO_TYPE_LABELS,
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
    FOG_WAVE_COOLDOWN,
    FOG_WAVE_COUNT_BASE,
    FOG_WAVE_COUNT_PER_PLAYER,
    FOG_WAVE_MAX,
    FOG_WAVE_MAX_DIST,
    FOG_WAVE_MIN_DIST,
    FOG_SPAWNS_PER_TICK,
    ROOM_FOG_SPAWNS_PER_TICK,
    ROOM_FOG_WAVE_BASE,
    ROOM_FOG_WAVE_MAX,
    ROOM_FOG_PRESSURE_BONUS_REASONS,
    INFECTION_SOURCE_BASE,
    INFECTION_SOURCE_MAX,
    INFECTION_SOURCE_STEP,
    FIRE_INTERVAL,
    FACILITY_MED_HEAL_PER_SEC,
    FACILITY_SEARCH_SECONDS,
    FACILITY_TOXIC_DAMAGE_PER_SEC,
    INITIAL_ITEMS,
    INITIAL_ZOMBIES,
    INPUT_IDLE_TIMEOUT,
    INTEREST_RADIUS,
    ITEM_R,
    ITEM_SPAWN_DT,
    DYNAMIC_AOI_RADIUS_MAIN,
    DYNAMIC_AOI_RADIUS_ROOM,
    EVENT_INTEREST_RADIUS,
    EXTRACTION_CAPTURE_SECONDS,
    EXTRACTION_COUNT,
    EXTRACTION_DISCOVER_RADIUS,
    GAME_VERSION,
    ITEM_TYPES,
    LEADERBOARD_SIZE,
    LEAPER_COOLDOWN,
    LEAPER_MAX_RANGE,
    LEAPER_MIN_RANGE,
    LEAPER_SPEED_MULT,
    LEVEL_XP_BASE,
    MAG_SIZE,
    MAP_H,
    MAP_W,
    MATERIAL_PICKUP_MAX,
    MATERIAL_PICKUP_MIN,
    MAX_BULLETS,
    MAX_ITEMS,
    MAX_PLAYERS,
    MAX_RESERVE_BY_TYPE,
    MAX_PISTOL_RESERVE,
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
    MELEE_ARC,
    MELEE_AUTO_RANGE,
    MELEE_COOLDOWN,
    MELEE_DAMAGE,
    MELEE_KNOCKBACK,
    MELEE_RANGE,
    MISSION_CAPTURE_RADIUS,
    MISSION_CAPTURE_SECONDS,
    MISSION_DISCOVER_RADIUS,
    MISSION_MAX_DIST,
    MISSION_MIN_DIST,
    MISSION_REPAIR_AMOUNT,
    MISSION_REWARD_SCORE,
    MISSION_REWARD_XP,
    MOVE_ACCEL,
    MOVE_COLLISION_STEP,
    MOVE_DECEL,
    MUZZLE_FORWARD,
    NUKE_RADIUS,
    PLAYER_MAX_HP,
    PLAYER_INTEREST_RADIUS,
    PLAYER_STAGE_LIVES,
    PLAYER_R,
    PLAYER_SPD,
    PLAYER_STALE_TIMEOUT,
    PRESSURE_SPAWN_MAX_DIST,
    PRESSURE_SPAWN_MIN_DIST,
    PROTECT,
    PROTOCOL_VERSION,
    RAPID_FIRE_MULT,
    RELOAD_SECONDS,
    SERVER_DT,
    SERVER_TICK_HZ,
    SCREAMER_COOLDOWN,
    SCREAMER_RADIUS,
    SCREAMER_RALLY_MULT,
    SCREAMER_RALLY_SECONDS,
    SNAPSHOT_HZ,
    SPATIAL_CELL,
    SPREAD_ANGLE,
    START_AMMO_RESERVE,
    STORY_BEATS,
    TASK_DROP_CHANCE,
    TASK_PICKUPS_PER_STAGE,
    WAVE_BASE,
    WAVE_BURST_BASE,
    WAVE_BURST_MAX,
    WAVE_BURST_PER_PLAYER,
    WAVE_STEP,
    WEAPON_MAX_LEVEL,
    WEAPON_ORDER,
    WEAPON_PARTS_PER_UPGRADE,
    WEAPON_TYPES,
    VEHICLE_RAM_COOLDOWN,
    VEHICLE_RAM_DAMAGE,
    VEHICLE_SECONDS,
    VEHICLE_SPEED_MULT,
    PATHFIND_INTERVAL,
    PATHFIND_STUCK_REPATH_SECONDS,
    EXTRACTION_REVEAL_SPAWNS,
    EXTRACTION_CHARGE_SPAWN_DT,
    EXTRACTION_CHARGE_SPAWNS,
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


def weapon_meta(weapon_id):
    return WEAPON_TYPES.get(weapon_id, WEAPON_TYPES["pistol"])


def ammo_type_for_weapon(weapon_id):
    return weapon_meta(weapon_id).get("ammo_type", "pistol")


SCENE_MAIN = "main"
ROOM_SCENE_PREFIX = "room:"
ROOM_W = 1900
ROOM_H = 1180
ROOM_DOOR_RADIUS = 74
ROOM_PATHFIND_INTERVAL = 1.05
ROOM_PATH_GOAL_CELL = 120
ROOM_PATH_RECOMPUTES_PER_TICK = 4
ROOM_NAV_NEIGHBOR_LIMIT = 14
ROOM_PATH_ENDPOINT_NEIGHBORS = 10
STAGE_FAILURE_REASONS = frozenset(("wipe", "abandon", "extraction_failed"))
OBJECTIVE_ITEM_TYPES = frozenset(("fuse", "sample", "keycard", "lore"))
ROOM_HAZARD_DPS = {
    "lab": 0.9,
    "archive": 0.45,
    "security": 0.35,
    "morgue": 1.15,
}
ROOM_ENTRY_HINTS = {
    "medbay": "搜药柜：医疗包和少量补给，翻找会弄出声音。",
    "generator": "接入电力：消耗保险丝，扩大可见撤离情报。",
    "lab": "采集样本：获得样本和研究零件，房间会持续污染。",
    "armory": "搜武器柜：武器、弹药和零件，但警报可能响起。",
    "archive": "检索档案：获得 1 份档案碎片，房间会持续污染。",
    "security": "破解安保柜：消耗门禁卡，换取武器/零件和撤离情报。",
    "morgue": "翻检尸袋：持续掉血，换取样本和急救物资。",
}
ROOM_REWARD_TABLE = {
    "medbay": {
        "guaranteed": ("medkit",),
        "bonus": ("medkit", "ammo_pistol", "parts"),
        "bonus_count": 1,
        "status": "医疗物资已掉落",
    },
    "generator": {
        "guaranteed": ("parts",),
        "bonus": ("ammo_pistol", "shield"),
        "bonus_count": 1,
        "status": "电力恢复，维护箱已打开",
    },
    "lab": {
        "guaranteed": ("sample",),
        "bonus": ("parts", "ammo_pistol", "shield"),
        "bonus_count": 1,
        "status": "样本容器和研究物资已掉落",
    },
    "archive": {
        "guaranteed": ("lore",),
        "bonus": (),
        "bonus_count": 0,
        "status": "档案已掉落",
    },
    "security": {
        "guaranteed": ("parts",),
        "bonus": ("ammo_rifle", "ammo_smg", "shield"),
        "bonus_count": 1,
        "status": "安保柜物资已掉落",
    },
    "morgue": {
        "guaranteed": ("sample",),
        "bonus": ("medkit", "ammo_pistol", "parts"),
        "bonus_count": 1,
        "status": "样本和急救物资已掉落",
    },
}

TALENT_DEFS = {
    "vitality": {
        "name": "生命强化",
        "desc": "最大生命 +12，并立即止血",
        "max": 5,
        "base_cost": 2,
    },
    "agility": {
        "name": "轻装突进",
        "desc": "移动速度 +12，撤离冲刺更稳",
        "max": 4,
        "base_cost": 2,
    },
    "capacity": {
        "name": "弹匣扩容",
        "desc": "所有枪械弹匣 +2，并补充分类备用弹",
        "max": 4,
        "base_cost": 3,
    },
    "gunsmith": {
        "name": "武器改装",
        "desc": "提升武器等级，增加伤害和弹匣",
        "max": WEAPON_MAX_LEVEL - 1,
        "base_cost": WEAPON_PARTS_PER_UPGRADE,
    },
}


def talent_level(player, talent_id):
    return int(player.get("talents", {}).get(talent_id, 0))


def talent_cost(player, talent_id):
    meta = TALENT_DEFS.get(talent_id)
    if not meta:
        return 999
    level = talent_level(player, talent_id)
    if level >= meta["max"]:
        return 0
    return meta["base_cost"] + level * 2


class Game:
    def __init__(self, emitter=None):
        self.emit = emitter
        self.players = {}
        self._peak_players = 1
        self.zombies = {}
        self.bullets = {}
        self.items = {}
        self.obstacles = []
        self.obstacle_grid = {}
        self.maze_openings = {}
        self.maze_margin = (0, 0)
        self.maze_cols = MAZE_COLS
        self.maze_rows = MAZE_ROWS
        self.map_features = []
        self.room_scenes = {}
        self.room_nav_cache = {}
        self.facility_spawn_timer = 0.0
        self.lab_sample_until = 0.0
        self.floor_points = []
        self.spawn_point = (MAP_W // 2, MAP_H // 2)
        self.extract_point = (MAP_W // 2, MAP_H // 2)
        self.extractions = []
        self.task_counts = {"fuse": 0, "sample": 0, "keycard": 0}
        self.stage_director = {}
        self.next_stage_reveal = False
        self.mission = None
        self._next_z = 1
        self._next_b = 1
        self._next_i = 1
        self.wave = 1
        self.wave_remaining = self._wave_budget()
        self.infection_source_remaining = self._infection_source_budget()
        self.wave_kills = 0
        self.wave_announced = False
        self.zombie_spawn_timer = 0.0
        self.item_spawn_timer = 0.0
        self.director_timer = 0.0
        self.next_fog_wave_at = 0.0
        self.fog_active_until = 0.0
        self.pending_fog_spawns = []
        self.intermission = None
        self.running = False
        self.last_tick = time.monotonic()
        self.tick_id = 0
        self.perf = {
            "tick_ms": 0.0,
            "snap_ms": 0.0,
            "sync_ms": 0.0,
            "payload_bytes": 0.0,
            "payload_max_bytes": 0,
            "overlap_resolves": 0,
            "players": 0,
            "zombies": 0,
            "bullets": 0,
            "items": 0,
        }
        self._next_payload_perf_at = 0.0
        self._overlap_resolves_this_tick = 0
        self._room_path_recomputes_this_tick = 0
        self._gen_obstacles()
        self._start_stage_tasks()
        alive = max(1, sum(1 for p in self.players.values() if not p.get("dead") and not p.get("paused")))
        scale = 0.4 + 0.6 * alive / MAX_PLAYERS
        initial_count = min(int((INITIAL_ZOMBIES + self.wave * 4) * scale), self.wave_remaining)
        for _ in range(initial_count):
            if self.spawn_zombie(emit=False):
                self.wave_remaining -= 1
        for _ in range(INITIAL_ITEMS * self._peak_players):
            self.spawn_item(emit=False)

    @property
    def _max_items(self):
        return MAX_ITEMS * self._peak_players

    def _wave_budget(self):
        base = WAVE_BASE + (self.wave - 1) * WAVE_STEP
        alive = max(1, sum(1 for p in self.players.values() if not p.get("dead")))
        return max(1, int(base * (0.4 + 0.6 * alive / MAX_PLAYERS)))

    def _infection_source_budget(self):
        return min(INFECTION_SOURCE_MAX, INFECTION_SOURCE_BASE + (self.wave - 1) * INFECTION_SOURCE_STEP)

    def _task_summary(self):
        return {
            "fuse": self.task_counts.get("fuse", 0),
            "sample": self.task_counts.get("sample", 0),
            "keycard": self.task_counts.get("keycard", 0),
            "lore": self._resource_count("lore"),
        }

    def _requires_text(self, requires):
        names = {"fuse": "保险丝", "sample": "病毒样本", "keycard": "门禁卡", "lore": "档案"}
        parts = []
        for typ, needed in requires.items():
            have = self._resource_count(typ)
            parts.append(f"{names.get(typ, typ)} {have}/{needed}")
        return " · ".join(parts) if parts else "无需额外物资"

    def _resource_count(self, typ):
        if typ == "lore":
            return sum(player.get("lore", 0) for player in self.players.values())
        return self.task_counts.get(typ, 0)

    def _exit_ready(self, exit_point):
        return all(self._resource_count(typ) >= needed for typ, needed in exit_point.get("requires", {}).items())

    def _service_ammo_reward_amounts(self):
        return {
            "pistol": 34 + min(20, self.wave * 2),
            "rifle": 16 + min(16, self.wave * 2),
            "smg": 42 + min(28, self.wave * 3),
            "shell": 6 + min(6, self.wave // 2),
        }

    def _ammo_reward_text(self, amounts):
        parts = [
            f"{AMMO_TYPE_LABELS.get(ammo_type, ammo_type)} +{amount}"
            for ammo_type, amount in amounts.items()
            if amount > 0
        ]
        return "全队补充：" + "、".join(parts)

    def _stage_director_for_wave(self):
        variants = [
            {
                "id": "blackout",
                "title": "恢复黑区供电",
                "hint": "先找保险丝点亮一段走廊，再决定从哪条撤离路线离开。",
                "focus": "fuse",
                "hook": "广播短暂恢复，提到下一层有一间没有编号的病房。",
            },
            {
                "id": "autopsy",
                "title": "采集变异样本",
                "hint": "特殊感染体身上有样本，越靠近实验区掉落概率越高。",
                "focus": "sample",
                "hook": "样本管里浮出一串名字，队伍里有人被标记为阳性。",
            },
            {
                "id": "lockdown",
                "title": "解除安保封锁",
                "hint": "门禁卡通常在重型感染体身上，打不掉就换另一条路。",
                "focus": "keycard",
                "hook": "安保日志显示，电梯已经载着同一批人下行了 17 次。",
            },
            {
                "id": "archive",
                "title": "抢救黑匣档案",
                "hint": "保险丝开柜，样本骗过扫描，门禁卡决定哪条路能活着走。",
                "focus": "mixed",
                "hook": "档案缺失的最后一页，似乎在更深处主动等你。",
            },
        ]
        return variants[(self.wave - 1) % len(variants)]

    def _directed_requires(self, route_type, base):
        requires = dict(base)
        focus = (self.stage_director or {}).get("focus")
        if focus == "fuse" and route_type == "service":
            requires["fuse"] = max(1, requires.get("fuse", 0) - 1)
        elif focus == "sample" and route_type == "lab":
            requires["sample"] = max(1, requires.get("sample", 0) - 1)
        elif focus == "keycard" and route_type == "security":
            requires["keycard"] = max(1, requires.get("keycard", 0))
            requires["sample"] = max(0, requires.get("sample", 0) - 1)
        elif focus == "mixed":
            if route_type == "service":
                requires["sample"] = max(1, requires.get("sample", 0) + 1)
            elif route_type == "lab":
                requires["fuse"] = max(1, requires.get("fuse", 0) + 1)
            else:
                requires["keycard"] = max(1, requires.get("keycard", 0))
        return {key: value for key, value in requires.items() if value > 0}

    def _route_reward_payload(self, exit_point):
        route = exit_point.get("type", "exit") if exit_point else "exit"
        rewards = {
            "service": {
                "route": "service",
                "rewardTitle": "弹药缓存",
                "rewardText": self._ammo_reward_text(self._service_ammo_reward_amounts()),
                "shortReward": "常规弹药",
                "routeHook": "维修通道深处传来金属敲击，像有人在给下一层装弹。",
            },
            "lab": {
                "route": "lab",
                "rewardTitle": "净化情报",
                "rewardText": "下一层提前暴露一个撤离终端，并获得额外档案线索。",
                "shortReward": "情报",
                "routeHook": "净化扫描吐出一张旧照片，照片背面写着你的名字。",
            },
            "security": {
                "route": "security",
                "rewardTitle": "安保武备",
                "rewardText": "全队获得武器零件，并优先解锁一把未发现武器。",
                "shortReward": "武备",
                "routeHook": "电梯面板亮起 B13，但设施蓝图里没有这一层。",
            },
            "archive": {
                "route": "archive",
                "rewardTitle": "档案门",
                "rewardText": "高危撤离：全队获得爆破弹 +1、保护罩掉落，并额外拼合档案线索。",
                "shortReward": "爆破弹/护盾/线索",
                "routeHook": "档案门背后没有出口，只有更深一层的撤离名单。",
            },
        }
        return rewards.get(route, {
            "route": route,
            "rewardTitle": "撤离成功",
            "rewardText": "队伍带着线索进入下一层。",
            "shortReward": "线索",
            "routeHook": (self.stage_director or {}).get("hook", ""),
        })

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

        tier = min(3, max(0, (self.wave - 1) // 2))
        templates = [
            ("service", "维修通道", {"fuse": 2 + tier}, "找到保险丝，恢复卷帘门供电"),
            ("lab", "净化闸门", {"sample": 3 + tier}, "击杀感染体取得样本，骗过净化扫描"),
            (
                "security",
                "安保电梯",
                {"keycard": 1 + (1 if self.wave >= 4 else 0), "sample": 1 + tier},
                "夺取门禁卡并提交样本",
            ),
            (
                "archive",
                "档案门",
                {"lore": 1 + tier, "keycard": 1 + (1 if self.wave >= 5 else 0), "sample": 2 + tier},
                "拼合黑匣档案并用样本骗过门后扫描",
            ),
        ]
        exits = []
        for idx, (point, spec) in enumerate(zip(selected, templates)):
            typ, name, requires, text = spec
            reward = self._route_reward_payload({"type": typ})
            exits.append({
                "id": f"{typ}-{self.wave}",
                "type": typ,
                "name": name,
                "text": text,
                "requires": self._directed_requires(typ, requires),
                "x": point[0],
                "y": point[1],
                "radius": MISSION_CAPTURE_RADIUS,
                "charge": 0.0,
                "visible": False,
                "done": False,
                "alarm_spawned": False,
                "charge_spawn": 0.0,
                "ready_notified": False,
                "wave": self.wave,
                "color": ("#66d9ff", "#b7ff47", "#d98cff", "#ff8fb6")[idx],
                "rewardTitle": reward["rewardTitle"],
                "rewardText": reward["rewardText"],
                "shortReward": reward["shortReward"],
                "routeHook": reward["routeHook"],
            })
        return exits

    def _start_stage_tasks(self):
        self.stage_director = self._stage_director_for_wave()
        self.task_counts = {"fuse": 0, "sample": 0, "keycard": 0}
        self.lab_sample_until = 0.0
        self.power_on = False
        self.extractions = self._new_extractions()
        self.mission = self.extractions[0] if self.extractions else None
        fuse_goal = max((exit_point.get("requires", {}).get("fuse", 0) for exit_point in self.extractions), default=0)
        fuse_spawns = min(TASK_PICKUPS_PER_STAGE - (1 if self.wave <= 2 else 0), max(2, fuse_goal + 1))
        for _ in range(fuse_spawns):
            self.spawn_item(item_type="fuse", emit=False)
        if (self.stage_director or {}).get("focus") == "sample":
            for _ in range(2):
                self.spawn_item(item_type="ammo", emit=False)
        self._seed_facility_rewards()

    def _new_mission(self):
        self.stage_director = self._stage_director_for_wave()
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
                "rewardTitle": exit_point.get("rewardTitle", ""),
                "rewardText": exit_point.get("rewardText", ""),
                "shortReward": exit_point.get("shortReward", ""),
                "routeHook": exit_point.get("routeHook", ""),
            })
        else:
            payload.update({
                "shortReward": exit_point.get("shortReward", ""),
                "rewardTitle": exit_point.get("rewardTitle", ""),
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

    def _is_boss_wave(self, wave=None):
        target_wave = self.wave if wave is None else int(wave)
        return target_wave > 0 and target_wave % BOSS_WAVE_INTERVAL == 0

    def _is_final_wave(self, wave=None):
        target_wave = self.wave if wave is None else int(wave)
        return target_wave == CAMPAIGN_FINAL_WAVE

    def _story_for_wave(self):
        beat = STORY_BEATS[(self.wave - 1) % len(STORY_BEATS)]
        return beat.format(wave=self.wave)

    def _objective_snapshot(self, full=True):
        if self.intermission:
            ending = bool(self.intermission.get("ending"))
            payload = {
                "remaining": 0,
                "budget": max(1, self._wave_budget()),
                "progress": 1,
                "boss": False,
                "task": self._task_summary(),
                "lore": sum(player.get("lore", 0) for player in self.players.values()),
                "loreTotal": len(CASE_FILES),
                "visibleExits": len([exit_point for exit_point in self.extractions if exit_point.get("visible")]),
                "readyExits": 0,
                "stageId": "intermission",
                "stageTitle": "撤离整备",
                "infectionSource": 0,
                "powered": bool(getattr(self, "power_on", False)),
            }
            if full:
                payload.update({
                    "title": "主线结局" if ending else "撤离整备",
                    "text": "真相已经揭露；可继续进入深层无尽模式。" if ending else "阅读档案，使用背包零件升级天赋，然后进入下一层。",
                    "story": self.intermission.get("endingText") if ending else (self.intermission.get("routeHook") or self._story_for_wave()),
                    "hook": self.intermission.get("routeHook", ""),
                })
            return payload
        budget = max(1, self._wave_budget())
        main_zombies = self._scene_zombie_count(SCENE_MAIN)
        remaining = max(0, self.wave_remaining + main_zombies)
        killed = max(0, min(budget, budget - remaining))
        boss_alive = any(
            zombie.get("type") == "boss" and self._entity_scene(zombie) == SCENE_MAIN
            for zombie in self.zombies.values()
        )
        visible_exits = [exit_point for exit_point in self.extractions if exit_point.get("visible")]
        ready_exits = [exit_point for exit_point in visible_exits if self._exit_ready(exit_point)]
        charging = next((exit_point for exit_point in self.extractions if exit_point.get("charge", 0) > 0), None)
        task = self._task_summary()
        lore_count = sum(player.get("lore", 0) for player in self.players.values())
        director = self.stage_director or self._stage_director_for_wave()
        if charging:
            title = charging["name"]
            if self._exit_ready(charging):
                text = f"撤离中 {round(charging['charge'] * 100)}% · 留在终端范围内撑住"
            else:
                text = f"撤离失败，缺：{self._requires_text(charging.get('requires', {}))}"
        elif ready_exits:
            title = "可撤离"
            text = f"{ready_exits[0]['name']} 条件满足，进入终端范围等待 {EXTRACTION_CAPTURE_SECONDS:.1f}s"
        elif boss_alive:
            title = "重型感染体"
            text = "它身上可能有门禁卡，打倒它再撤"
        elif visible_exits:
            title = "撤离点已发现"
            text = f"{visible_exits[0]['name']} 需要：{self._requires_text(visible_exits[0].get('requires', {}))}"
        else:
            title = director.get("title", "找到撤离终端")
            text = director.get("hint", "先探索设施边缘，靠近撤离终端后显示条件。")
        progress = charging.get("charge", 0) if charging else min(1, killed / budget)
        payload = {
            "remaining": remaining,
            "budget": budget,
            "progress": round(max(0, min(1, progress)), 3),
            "boss": self._is_boss_wave() or boss_alive,
            "task": task,
            "lore": lore_count,
            "loreTotal": len(CASE_FILES),
            "visibleExits": len(visible_exits),
            "readyExits": len(ready_exits),
            "stageId": director.get("id", ""),
            "stageTitle": director.get("title", ""),
            "infectionSource": max(0, self.infection_source_remaining),
            "powered": bool(getattr(self, "power_on", False)),
        }
        if full:
            payload.update({
                "title": title,
                "text": text,
                "story": self._story_for_wave(),
                "hook": director.get("hook", ""),
            })
        return payload

    def _talent_snapshot(self, player):
        if not player:
            return {}
        talents = player.setdefault("talents", {})
        return {
            tid: {
                "id": tid,
                "name": meta["name"],
                "desc": meta["desc"],
                "level": int(talents.get(tid, 0)),
                "max": meta["max"],
                "cost": talent_cost(player, tid),
            }
            for tid, meta in TALENT_DEFS.items()
        }

    def _intermission_snapshot(self, sid=None):
        if not self.intermission:
            return None
        ready = set(self.intermission.get("ready", []))
        player = self.players.get(sid) if sid else None
        return {
            "active": True,
            "ending": bool(self.intermission.get("ending")),
            "clearedWave": self.intermission.get("clearedWave", self.wave),
            "nextWave": self.intermission.get("nextWave", self.wave + 1),
            "name": self.intermission.get("name", "撤离终端"),
            "rewardTitle": self.intermission.get("rewardTitle", ""),
            "rewardText": self.intermission.get("rewardText", ""),
            "routeHook": self.intermission.get("routeHook", ""),
            "endingTitle": self.intermission.get("endingTitle", ""),
            "endingText": self.intermission.get("endingText", ""),
            "route": self.intermission.get("route", ""),
            "ready": len(ready),
            "players": len(self.players),
            "youReady": bool(sid and sid in ready),
            "nextBoss": self._is_boss_wave(self.intermission.get("nextWave", self.wave + 1)),
            "bossEvery": BOSS_WAVE_INTERVAL,
            "bossName": "黑墙巨像",
            "finalWave": CAMPAIGN_FINAL_WAVE,
            "talents": self._talent_snapshot(player),
        }

    def _player_speed(self, player, now=0.0):
        base = player_speed(player.get("level", 1)) + talent_level(player, "agility") * 12
        if now > 0:
            boost = 1.0
            if now < player.get("levelup_boost_until", 0):
                boost = max(boost, 1.22)
            if now < player.get("adrenaline_until", 0):
                boost = max(boost, 1.40)
            base *= boost
        return base

    def _max_reserve_for_player(self, player, ammo_type="pistol"):
        base = MAX_RESERVE_BY_TYPE.get(ammo_type, MAX_PISTOL_RESERVE)
        capacity = talent_level(player, "capacity")
        if ammo_type == "explosive":
            return base + min(2, capacity)
        if ammo_type == "shell":
            return base + capacity * 6
        return base + capacity * 18

    def _ammo_reserve_pool(self, player):
        pool = player.setdefault("ammo_reserve", {})
        for ammo_type, amount in START_AMMO_RESERVE.items():
            pool.setdefault(ammo_type, 0 if ammo_type != "pistol" else amount)
        return pool

    def _ammo_reserve(self, player, ammo_type=None):
        ammo_type = ammo_type or ammo_type_for_weapon(player.get("weapon_id", "pistol"))
        return max(0, int(self._ammo_reserve_pool(player).get(ammo_type, 0)))

    def _set_ammo_reserve(self, player, ammo_type, amount):
        pool = self._ammo_reserve_pool(player)
        capped = min(self._max_reserve_for_player(player, ammo_type), max(0, int(amount)))
        pool[ammo_type] = capped
        if ammo_type == ammo_type_for_weapon(player.get("weapon_id", "pistol")):
            player["current_reserve"] = capped
        return capped

    def _add_ammo_reserve(self, player, ammo_type, amount):
        return self._set_ammo_reserve(player, ammo_type, self._ammo_reserve(player, ammo_type) + amount)

    def _ammo_pool_snapshot(self, player):
        pool = self._ammo_reserve_pool(player)
        return ",".join(
            f"{ammo_type}:{max(0, int(pool.get(ammo_type, 0)))}"
            for ammo_type in AMMO_TYPE_LABELS.keys()
        )

    def _current_ammo_payload(self, player, ammo_type=None):
        ammo_type = ammo_type or ammo_type_for_weapon(player.get("weapon_id", "pistol"))
        return {
            "ammoType": ammo_type,
            "ammoTypeName": AMMO_TYPE_LABELS.get(ammo_type, "备用弹"),
            "ammoPools": self._ammo_pool_snapshot(player),
            "currentReserve": self._ammo_reserve(player, ammo_type),
        }

    def _apply_talent_effects(self, player, talent_id, now):
        if talent_id == "vitality":
            base = PLAYER_MAX_HP + min(45, (player.get("level", 1) - 1) * 5)
            player["max_hp"] = base + talent_level(player, "vitality") * 12
            player["hp"] = min(player["max_hp"], player.get("hp", player["max_hp"]) + 18)
        elif talent_id == "capacity":
            self._sync_weapon_fields(player)
            for ammo_type, bonus in (("pistol", 18), ("rifle", 14), ("smg", 24), ("shell", 4)):
                self._add_ammo_reserve(player, ammo_type, bonus)
        elif talent_id == "gunsmith":
            player["weapon_level"] = min(WEAPON_MAX_LEVEL, player.get("weapon_level", 1) + 1)
            self._sync_weapon_fields(player)
            player["ammo"] = min(player["mag_size"], player.get("ammo", 0) + 2)
            self._weapon_state(player)["ammo"] = player["ammo"]
        elif talent_id == "agility":
            player["shield_until"] = max(player.get("shield_until", 0), now + 2.0)

    def buy_talent(self, sid, talent_id):
        player = self.players.get(sid)
        talent_id = str(talent_id or "").strip().lower()
        meta = TALENT_DEFS.get(talent_id)
        if not player or not meta:
            return False
        if not self.intermission:
            self._emit_to("talent_denied", {
                "pid": sid,
                "reason": "只能在撤离整备阶段升级",
                "col": "#ffb1bd",
            }, [sid])
            return False
        talents = player.setdefault("talents", {})
        level = int(talents.get(talent_id, 0))
        if level >= meta["max"]:
            self._emit_to("talent_denied", {
                "pid": sid,
                "reason": f"{meta['name']} 已满级",
                "col": "#aeb7c2",
            }, [sid])
            return False
        cost = talent_cost(player, talent_id)
        if player.get("materials", 0) < cost:
            self._emit_to("talent_denied", {
                "pid": sid,
                "reason": f"零件不足：需要 {cost}",
                "col": "#ffc247",
            }, [sid])
            return False
        player["materials"] -= cost
        talents[talent_id] = level + 1
        self._apply_talent_effects(player, talent_id, self._now())
        payload = {
            "pid": sid,
            "talent": talent_id,
            "name": meta["name"],
            "level": talents[talent_id],
            "materials": player.get("materials", 0),
            "maxHp": player.get("max_hp", PLAYER_MAX_HP),
            "hp": player.get("hp", PLAYER_MAX_HP),
            "ammo": player.get("ammo", MAG_SIZE),
            "magSize": player.get("mag_size", MAG_SIZE),
            "weaponLevel": player.get("weapon_level", 1),
            "speed": self._player_speed(player),
            "talents": self._talent_snapshot(player),
            "intermission": self._intermission_snapshot(sid),
            "col": "#48f0a0",
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
        }
        payload.update(self._current_ammo_payload(player))
        self._emit_to("talent_upgrade", payload, [sid])
        return True

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

    def _emit_near(self, event, data, x, y, radius=EVENT_INTEREST_RADIUS, include=None, scene=SCENE_MAIN):
        targets = []
        event_scene = scene or data.get("scene") or SCENE_MAIN
        radius_sq = radius * radius
        for sid, player in self.players.items():
            if self._entity_scene(player) != event_scene:
                continue
            if (player["x"] - x) ** 2 + (player["y"] - y) ** 2 <= radius_sq:
                targets.append(sid)
        if include:
            targets.append(include)
        payload = dict(data)
        payload.setdefault("sceneId", event_scene)
        self._emit_to(event, payload, targets)

    def _now(self):
        return time.monotonic()

    def _record_tick_perf(self, started):
        elapsed = (time.perf_counter() - started) * 1000
        old = self.perf.get("tick_ms", 0.0)
        self.perf["tick_ms"] = elapsed if old <= 0 else old * 0.85 + elapsed * 0.15
        self.perf["overlap_resolves"] = self._overlap_resolves_this_tick
        self._overlap_resolves_this_tick = 0
        self.perf["players"] = len(self.players)
        self.perf["zombies"] = len(self.zombies)
        self.perf["bullets"] = len(self.bullets)
        self.perf["items"] = len(self.items)

    def _record_snapshot_perf(self, started):
        elapsed = (time.perf_counter() - started) * 1000
        old = self.perf.get("snap_ms", 0.0)
        self.perf["snap_ms"] = elapsed if old <= 0 else old * 0.85 + elapsed * 0.15

    def _record_payload_perf(self, snapshots):
        now = time.perf_counter()
        if self.perf.get("payload_max_bytes", 0) and now < self._next_payload_perf_at:
            return
        self._next_payload_perf_at = now + 0.75
        sizes = [
            len(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
            for snapshot in snapshots
        ]
        if not sizes:
            return
        avg_size = sum(sizes) / len(sizes)
        old = self.perf.get("payload_bytes", 0.0)
        self.perf["payload_bytes"] = avg_size if old <= 0 else old * 0.85 + avg_size * 0.15
        self.perf["payload_max_bytes"] = max(sizes)

    def _perf_snapshot(self):
        return {
            "tick_ms": round(self.perf.get("tick_ms", 0.0), 2),
            "snap_ms": round(self.perf.get("snap_ms", 0.0), 2),
            "sync_ms": round(self.perf.get("sync_ms", 0.0), 2),
            "payload_bytes": round(self.perf.get("payload_bytes", 0.0), 1),
            "payload_max_bytes": int(self.perf.get("payload_max_bytes", 0)),
            "overlap_resolves": int(self.perf.get("overlap_resolves", 0)),
            "players": len(self.players),
            "zombies": len(self.zombies),
            "bullets": len(self.bullets),
            "items": len(self.items),
            "fog_queue": self._pending_fog_spawn_count(),
            "snapshot_hz": SNAPSHOT_HZ,
        }

    def _gen_obstacles(self):
        self.obstacles = []
        self.map_features = []
        layouts = [(12, 9), (10, 11), (9, 12), (11, 10)]
        self.maze_cols, self.maze_rows = layouts[(self.wave - 1) % len(layouts)]
        cols = self.maze_cols
        rows = self.maze_rows
        margin_x = (MAP_W - cols * MAZE_CELL) / 2
        margin_y = (MAP_H - rows * MAZE_CELL) / 2
        mid = rows // 2
        start = (0, mid)
        active = set()

        def add_cell(cell):
            c, r = cell
            if 0 <= c < cols and 0 <= r < rows:
                active.add(cell)

        def carve_corridor(a, b):
            ac, ar = a
            bc, br = b
            step = 1 if bc >= ac else -1
            for c in range(ac, bc + step, step):
                add_cell((c, ar))
            step = 1 if br >= ar else -1
            for r in range(ar, br + step, step):
                add_cell((bc, r))

        for c in range(cols):
            add_cell((c, mid))

        room_specs = [
            ("medbay", "病房", 1 + (self.wave % 2), max(1, mid - 4), 3, 3),
            ("generator", "机房", max(2, cols - 5), 1 + (self.wave % 3 == 0), 3, 3),
            ("lab", "样本库", max(2, cols // 2 - 1), max(1, rows - 4), 3, 3),
            ("armory", "仓库", max(1, cols // 2 - 4), max(1, mid - 2), 2, 4),
            ("archive", "档案室", max(1, cols // 2 + 2), max(1, mid + 2), 2, 3),
            ("security", "安保室", max(1, cols - 3), max(1, mid - 2), 2, 3),
            ("morgue", "停尸间", max(1, cols // 3), max(1, rows - 3), 2, 2),
        ]
        for effect, label, rc, rr, rw, rh in room_specs:
            center = (min(cols - 1, rc + rw // 2), min(rows - 1, rr + rh // 2))
            carve_corridor((center[0], mid), center)
            for c in range(rc, min(cols, rc + rw)):
                for r in range(rr, min(rows, rr + rh)):
                    add_cell((c, r))
            fx, fy = (
                margin_x + center[0] * MAZE_CELL + MAZE_CELL / 2,
                margin_y + center[1] * MAZE_CELL + MAZE_CELL / 2,
            )
            self.map_features.append({
                "kind": "room",
                "id": f"{effect}-{self.wave}",
                "scene_id": f"{ROOM_SCENE_PREFIX}{effect}-{self.wave}",
                "effect": effect,
                "label": label,
                "x": round(fx - MAZE_CELL * 0.42, 1),
                "y": round(fy - MAZE_CELL * 0.34, 1),
                "w": round(MAZE_CELL * 0.84, 1),
                "h": round(MAZE_CELL * 0.68, 1),
                "active": True,
                "searched": False,
            })

        branch_budget = 8 + min(7, self.wave)
        for i in range(branch_budget):
            c = random.randrange(1, max(2, cols - 1))
            direction = -1 if (i + self.wave) % 2 == 0 else 1
            length = random.randint(2, max(3, rows // 2))
            end = (c, max(0, min(rows - 1, mid + direction * length)))
            carve_corridor((c, mid), end)
            if random.random() < 0.72:
                side = -1 if random.random() < 0.5 else 1
                add_cell((max(0, min(cols - 1, c + side)), end[1]))

        visited = {start}
        openings = {start: set()}
        stack = [start]

        def neighbors(cell):
            c, r = cell
            result = []
            if (c - 1, r) in active:
                result.append(("W", (c - 1, r), "E"))
            if (c + 1, r) in active:
                result.append(("E", (c + 1, r), "W"))
            if (c, r - 1) in active:
                result.append(("N", (c, r - 1), "S"))
            if (c, r + 1) in active:
                result.append(("S", (c, r + 1), "N"))
            random.shuffle(result)
            return result

        while stack and len(visited) < len(active):
            cell = stack[-1]
            candidates = [(d, nxt, back) for d, nxt, back in neighbors(cell) if nxt not in visited]
            if not candidates:
                stack.pop()
                if not stack:
                    missing = [cell for cell in active if cell not in visited]
                    if missing:
                        bridge = min(missing, key=lambda p: abs(p[0] - start[0]) + abs(p[1] - start[1]))
                        carve_corridor(start, bridge)
                        visited.add(bridge)
                        openings.setdefault(bridge, set())
                        stack.append(bridge)
                continue
            direction, nxt, back = candidates[0]
            openings.setdefault(cell, set()).add(direction)
            openings.setdefault(nxt, set()).add(back)
            visited.add(nxt)
            stack.append(nxt)

        extra_links = max(4, MAZE_EXTRA_LINKS + min(4, self.wave // 2))
        active_list = list(active)
        for _ in range(extra_links):
            cell = random.choice(active_list)
            choices = neighbors(cell)
            if not choices:
                continue
            direction, nxt, back = random.choice(choices)
            openings.setdefault(cell, set()).add(direction)
            openings.setdefault(nxt, set()).add(back)

        def center(cell):
            c, r = cell
            return (
                margin_x + c * MAZE_CELL + MAZE_CELL / 2,
                margin_y + r * MAZE_CELL + MAZE_CELL / 2,
            )

        self.floor_points = [center(cell) for cell in sorted(active)]
        self.spawn_point = center(start)
        self.extract_point = center(max(active, key=lambda cell: (cell[0] - start[0]) ** 2 + (cell[1] - start[1]) ** 2))

        wall_keys = set()

        def add_wall(x, y, w, h, kind="wall"):
            key = (round(x, 1), round(y, 1), round(w, 1), round(h, 1), kind)
            if key in wall_keys:
                return
            wall_keys.add(key)
            self.obstacles.append({
                "x": round(x, 1),
                "y": round(y, 1),
                "w": round(w, 1),
                "h": round(h, 1),
                "kind": kind,
            })

        wall = MAZE_WALL
        for cell in active:
            c, r = cell
            x = margin_x + c * MAZE_CELL
            y = margin_y + r * MAZE_CELL
            cell_openings = openings.get(cell, set())
            if "N" not in cell_openings:
                add_wall(x - wall / 2, y - wall / 2, MAZE_CELL + wall, wall)
            if "S" not in cell_openings:
                add_wall(x - wall / 2, y + MAZE_CELL - wall / 2, MAZE_CELL + wall, wall)
            if "W" not in cell_openings:
                add_wall(x - wall / 2, y - wall / 2, wall, MAZE_CELL + wall)
            if "E" not in cell_openings:
                add_wall(x + MAZE_CELL - wall / 2, y - wall / 2, wall, MAZE_CELL + wall)

        prop_cells = [cell for cell in active if cell != start and abs(cell[0] - start[0]) + abs(cell[1] - start[1]) > 3]
        random.shuffle(prop_cells)
        prop_kinds = ("crate", "gurney", "generator", "tank", "locker")
        for idx, cell in enumerate(prop_cells[:min(18, 8 + self.wave * 2)]):
            if random.random() < 0.28:
                cx, cy = center(cell)
                kind = prop_kinds[idx % len(prop_kinds)]
                if kind in ("gurney", "locker"):
                    w, h = (72, 30) if random.random() < 0.5 else (30, 72)
                elif kind == "generator":
                    w, h = 78, 54
                elif kind == "tank":
                    w, h = 52, 52
                else:
                    w, h = 54, 46
                add_wall(cx - w / 2, cy - h / 2, w, h, kind=kind)
            elif random.random() < 0.55:
                cx, cy = center(cell)
                self.map_features.append({
                    "kind": random.choice(("blood", "light", "warning", "pool")),
                    "x": round(cx + random.uniform(-54, 54), 1),
                    "y": round(cy + random.uniform(-54, 54), 1),
                    "w": round(random.uniform(34, 86), 1),
                    "h": round(random.uniform(18, 62), 1),
                })
        self.maze_openings = openings
        self.maze_margin = (margin_x, margin_y)
        self._build_room_scenes()
        self._index_obstacles()

    def _build_room_scenes(self):
        self.room_scenes = {}
        self._invalidate_room_nav_cache()
        palettes = {
            "medbay": "#48f0a0",
            "generator": "#66d9ff",
            "lab": "#b7ff47",
            "armory": "#ffc247",
            "archive": "#aee6ff",
            "security": "#d98cff",
            "morgue": "#b7ff47",
        }
        for room in [f for f in self.map_features if f.get("kind") == "room"]:
            scene_id = room.get("scene_id") or f"{ROOM_SCENE_PREFIX}{room['id']}"
            room["scene_id"] = scene_id
            effect = room.get("effect", "room")
            tint = palettes.get(effect, "#dce7f1")
            w, h = ROOM_W, ROOM_H
            door_y = h / 2
            door_gap = 190
            obs = []

            def wall(x, y, ww, hh, kind="wall"):
                obs.append({
                    "x": round(x, 1),
                    "y": round(y, 1),
                    "w": round(ww, 1),
                    "h": round(hh, 1),
                    "kind": kind,
                })

            wall(80, 72, w - 160, 42)
            wall(80, h - 114, w - 160, 42)
            wall(w - 122, 72, 42, h - 144)
            wall(80, 72, 42, door_y - door_gap / 2 - 72)
            wall(80, door_y + door_gap / 2, 42, h - 114 - (door_y + door_gap / 2))
            wall(w * 0.55, h * 0.34, 54, h * 0.38, "bulkhead")

            features = [
                {
                    "kind": "room",
                    "id": f"{room['id']}-interior",
                    "effect": effect,
                    "label": room.get("label", "设施"),
                    "x": 126,
                    "y": 118,
                    "w": w - 252,
                    "h": h - 236,
                    "active": room.get("active", True),
                    "searched": room.get("searched", False),
                },
                {
                    "kind": "door",
                    "id": f"{room['id']}-exit",
                    "label": "返回走廊",
                    "x": 92,
                    "y": round(door_y - 72, 1),
                    "w": 64,
                    "h": 144,
                    "color": tint,
                },
            ]

            if effect == "medbay":
                for i in range(4):
                    x = 300 + i % 2 * 360
                    y = 250 + i // 2 * 330
                    wall(x, y, 138, 42, "gurney")
                features.append({"kind": "blood", "x": 1120, "y": 740, "w": 130, "h": 68})
            elif effect == "generator":
                wall(420, 260, 160, 92, "generator")
                wall(1130, 630, 220, 70, "generator")
                features.append({"kind": "warning", "x": 980, "y": 230, "w": 260, "h": 140})
            elif effect == "lab":
                for i in range(5):
                    wall(330 + i * 240, 270 + (i % 2) * 260, 74, 112, "tank")
                features.append({"kind": "pool", "x": 1320, "y": 760, "w": 160, "h": 86})
            elif effect == "armory":
                for i in range(5):
                    wall(300 + i * 220, 320 + (i % 2) * 260, 120, 54, "locker")
                features.append({"kind": "warning", "x": 1150, "y": 240, "w": 180, "h": 110})
            elif effect == "archive":
                for i in range(6):
                    wall(300 + i * 180, 250 + (i % 3) * 190, 90, 140, "locker")
                features.append({"kind": "blood", "x": 1280, "y": 620, "w": 92, "h": 48})
            elif effect == "security":
                wall(420, 300, 220, 74, "locker")
                wall(1050, 250, 270, 58, "generator")
                features.append({"kind": "warning", "x": 920, "y": 610, "w": 300, "h": 160})
            elif effect == "morgue":
                for i in range(6):
                    wall(300 + (i % 3) * 260, 270 + (i // 3) * 300, 150, 38, "gurney")
                features.append({"kind": "blood", "x": 1220, "y": 760, "w": 180, "h": 96})
                features.append({"kind": "pool", "x": 1010, "y": 470, "w": 120, "h": 66})

            self.room_scenes[scene_id] = {
                "id": scene_id,
                "room_id": room["id"],
                "effect": effect,
                "name": room.get("label", "设施"),
                "mw": w,
                "mh": h,
                "spawn": (240, door_y),
                "exit": {"x": 130, "y": door_y, "radius": ROOM_DOOR_RADIUS},
                "loot": {"x": 250, "y": 170, "w": w - 420, "h": h - 340},
                "nav_points": [
                    (w * 0.47, 310),
                    (w * 0.64, 310),
                    (w * 0.47, h - 250),
                    (w * 0.64, h - 250),
                    (260, door_y),
                    (w - 260, door_y),
                ],
                "zombie_points": [
                    (w - 240, 190),
                    (w - 260, h - 210),
                    (w * 0.68, 180),
                    (w * 0.72, h - 190),
                    (w * 0.44, h - 190),
                ],
                "obs": obs,
                "features": features,
            }

    def _cell_center(self, cell):
        """Get world coordinates for a maze cell center."""
        c, r = cell
        mx, my = self.maze_margin
        return (mx + c * MAZE_CELL + MAZE_CELL / 2, my + r * MAZE_CELL + MAZE_CELL / 2)

    def _world_to_cell(self, x, y):
        """Convert world coordinates to the nearest maze cell."""
        mx, my = self.maze_margin
        c = int((x - mx) / MAZE_CELL)
        r = int((y - my) / MAZE_CELL)
        c = max(0, min(getattr(self, "maze_cols", MAZE_COLS) - 1, c))
        r = max(0, min(getattr(self, "maze_rows", MAZE_ROWS) - 1, r))
        return (c, r)

    def _portal_between(self, cell_a, cell_b):
        if abs(cell_a[0] - cell_b[0]) + abs(cell_a[1] - cell_b[1]) != 1:
            return None
        ax, ay = self._cell_center(cell_a)
        bx, by = self._cell_center(cell_b)
        return ((ax + bx) / 2, (ay + by) / 2)

    def _find_path_astar(self, start_cell, end_cell):
        """A* pathfinding on the maze cell grid. Returns a list of cells."""
        if start_cell == end_cell:
            return [start_cell]
        if not self.maze_openings:
            return [start_cell, end_cell]

        dir_delta = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
        reverse_dir = {"N": "S", "S": "N", "E": "W", "W": "E"}
        counter = 0
        open_set = [(0, counter, start_cell)]
        came_from = {}
        g_score = {start_cell: 0}
        closed = set()
        end_center = self._cell_center(end_cell)

        while open_set:
            _, _, current = heapq.heappop(open_set)
            if current in closed:
                continue
            closed.add(current)

            if current == end_cell:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            openings = self.maze_openings.get(current, set())
            for direction in openings:
                dc, dr = dir_delta[direction]
                neighbor = (current[0] + dc, current[1] + dr)
                if (
                    neighbor[0] < 0
                    or neighbor[0] >= getattr(self, "maze_cols", MAZE_COLS)
                    or neighbor[1] < 0
                    or neighbor[1] >= getattr(self, "maze_rows", MAZE_ROWS)
                ):
                    continue
                if neighbor in closed:
                    continue
                if reverse_dir[direction] not in self.maze_openings.get(neighbor, set()):
                    continue
                move_cost = MAZE_CELL
                tentative_g = g_score[current] + move_cost
                if tentative_g < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    nc = self._cell_center(neighbor)
                    h = math.hypot(end_center[0] - nc[0], end_center[1] - nc[1])
                    counter += 1
                    heapq.heappush(open_set, (tentative_g + h, counter, neighbor))

        return [start_cell, end_cell]

    def _zombie_waypoint(self, zombie, target, now):
        """Compute the next maze-aware waypoint for a zombie."""
        if self._entity_scene(zombie) != SCENE_MAIN:
            return self._room_zombie_waypoint(zombie, target, now)
        target_id = target.get("id")
        start_cell = self._world_to_cell(zombie["x"], zombie["y"])
        end_cell = self._world_to_cell(target["x"], target["y"])
        if start_cell == end_cell:
            zombie["path"] = [start_cell]
            zombie["path_kind"] = "main"
            zombie["path_target"] = target_id
            zombie["path_goal"] = end_cell
            zombie["path_time"] = now
            zombie["path_idx"] = 1
            return target
        if not self.maze_openings:
            return target

        need_recompute = (
            zombie.get("path_kind") != "main"
            or
            zombie.get("path_target") != target_id
            or zombie.get("path_goal") != end_cell
            or now - zombie.get("path_time", 0) > PATHFIND_INTERVAL
            or zombie.get("path") is None
        )
        if need_recompute:
            path = self._find_path_astar(start_cell, end_cell)
            zombie["path"] = path
            zombie["path_kind"] = "main"
            zombie["path_target"] = target_id
            zombie["path_goal"] = end_cell
            zombie["path_time"] = now
            zombie["path_idx"] = 1

        path = zombie.get("path", [])
        path_idx = zombie.get("path_idx", 1)
        if not path or path_idx >= len(path):
            return target

        if start_cell in path:
            path_idx = max(path_idx, path.index(start_cell) + 1)
        while path_idx < len(path) and path[path_idx] == start_cell:
            path_idx += 1
        zombie["path_idx"] = path_idx
        if path_idx >= len(path):
            return target

        next_cell = path[path_idx]
        portal = self._portal_between(start_cell, next_cell)
        if portal:
            portal_dist = math.hypot(zombie["x"] - portal[0], zombie["y"] - portal[1])
            if portal_dist > max(zombie["radius"] * 2.6, MAZE_WALL * 0.72):
                return {"x": portal[0], "y": portal[1], "id": target_id, "radius": target.get("radius", PLAYER_R)}

        waypoint = self._cell_center(next_cell)
        return {"x": waypoint[0], "y": waypoint[1], "id": target_id, "radius": target.get("radius", PLAYER_R)}

    def _room_zombie_waypoint(self, zombie, target, now):
        scene_id = self._entity_scene(zombie)
        path_radius = zombie.get("radius", 16) + 8
        if not self._segment_blocked(zombie["x"], zombie["y"], target["x"], target["y"], radius=path_radius, scene=scene_id):
            zombie["path"] = None
            zombie["path_kind"] = "room_direct"
            return target

        target_id = target.get("id")
        goal_key = (
            round(target["x"] / ROOM_PATH_GOAL_CELL),
            round(target["y"] / ROOM_PATH_GOAL_CELL),
        )
        path = zombie.get("path") if zombie.get("path_kind") == "room" else None
        retry_due = zombie.get("path_source") == "fallback" and now >= zombie.get("path_retry_at", 0)
        need_recompute = (
            not path
            or zombie.get("path_target") != target_id
            or zombie.get("path_goal") != goal_key
            or retry_due
            or now - zombie.get("path_time", 0) > ROOM_PATHFIND_INTERVAL
        )
        if need_recompute and path and self._room_path_recomputes_this_tick >= ROOM_PATH_RECOMPUTES_PER_TICK:
            need_recompute = False
        if need_recompute:
            can_recompute = self._room_path_recomputes_this_tick < ROOM_PATH_RECOMPUTES_PER_TICK
            source = "visibility"
            if can_recompute:
                self._room_path_recomputes_this_tick += 1
                path = self._room_visibility_path(scene_id, zombie, target, path_radius)
            else:
                source = "fallback"
                path = None
            if not path:
                source = "fallback"
                waypoint = self._room_fallback_waypoint(scene_id, zombie, target, path_radius)
                path = [(zombie["x"], zombie["y"]), (waypoint["x"], waypoint["y"])] if waypoint else []
            if not path:
                zombie["path"] = None
                zombie["path_kind"] = "room"
                zombie["path_source"] = "blocked"
                zombie["path_target"] = target_id
                zombie["path_goal"] = goal_key
                zombie["path_retry_at"] = now + 0.18
                return {"x": zombie["x"], "y": zombie["y"], "id": target_id, "radius": target.get("radius", PLAYER_R)}
            jitter = (int(zombie.get("id", 0)) % 13) * 0.055
            zombie["path"] = path
            zombie["path_kind"] = "room"
            zombie["path_source"] = source
            zombie["path_target"] = target_id
            zombie["path_goal"] = goal_key
            zombie["path_time"] = now + (jitter if source == "visibility" else 0)
            zombie["path_retry_at"] = now + 0.12 + jitter * 0.22 if source == "fallback" else 0
            zombie["path_idx"] = 1

        if path:
            path_idx = min(max(1, zombie.get("path_idx", 1)), len(path) - 1)
            while path_idx < len(path) - 1:
                wx, wy = path[path_idx]
                if math.hypot(zombie["x"] - wx, zombie["y"] - wy) > zombie.get("radius", 16) * 2.1:
                    break
                path_idx += 1
            zombie["path_idx"] = path_idx
            wx, wy = path[path_idx]
            if math.hypot(zombie["x"] - wx, zombie["y"] - wy) > zombie.get("radius", 16) * 2.1:
                return {"x": wx, "y": wy, "id": target_id, "radius": target.get("radius", PLAYER_R)}
        return target

    def _room_fallback_waypoint(self, scene_id, zombie, target, path_radius):
        scene = self._scene_def(scene_id)
        best = None
        for idx, point in enumerate(scene.get("nav_points", [])):
            wx, wy = point
            wx, wy = self._resolve_obstacle_overlap(wx, wy, zombie.get("radius", 16), scene_id)
            if math.hypot(zombie["x"] - wx, zombie["y"] - wy) < zombie.get("radius", 16) * 2.4:
                continue
            if any(circ_rect(wx, wy, zombie.get("radius", 16), o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(wx, wy, zombie.get("radius", 16) + MAZE_WALL + 4, scene=scene_id)):
                continue
            z_blocked = self._segment_blocked(zombie["x"], zombie["y"], wx, wy, radius=path_radius, scene=scene_id)
            target_blocked = self._segment_blocked(wx, wy, target["x"], target["y"], radius=path_radius, scene=scene_id)
            if z_blocked and target_blocked:
                continue
            score = (
                math.hypot(zombie["x"] - wx, zombie["y"] - wy)
                + math.hypot(target["x"] - wx, target["y"] - wy)
                + (5000 if z_blocked else 0)
                + (1600 if target_blocked else 0)
                + idx * 6
            )
            if best is None or score < best[0]:
                best = (score, wx, wy)
        if not best:
            return None
        _, wx, wy = best
        return {"x": wx, "y": wy, "id": target.get("id"), "radius": target.get("radius", PLAYER_R)}

    def _room_nav_point_clear(self, scene_id, x, y, radius):
        scene = self._scene_def(scene_id)
        mw = scene.get("mw", ROOM_W)
        mh = scene.get("mh", ROOM_H)
        if x < radius or y < radius or x > mw - radius or y > mh - radius:
            return False
        return not self._overlaps_obstacle(x, y, radius, scene_id)

    def _room_nav_points(self, scene_id, radius):
        scene = self._scene_def(scene_id)
        margin = radius + 22
        points = list(scene.get("nav_points", []))
        for obstacle in scene.get("obs", []):
            if obstacle.get("kind") == "wall":
                continue
            ox, oy = obstacle["x"], obstacle["y"]
            ow, oh = obstacle["w"], obstacle["h"]
            points.extend((
                (ox - margin, oy - margin),
                (ox + ow + margin, oy - margin),
                (ox - margin, oy + oh + margin),
                (ox + ow + margin, oy + oh + margin),
                (ox + ow / 2, oy - margin),
                (ox + ow / 2, oy + oh + margin),
                (ox - margin, oy + oh / 2),
                (ox + ow + margin, oy + oh / 2),
            ))
        clean = []
        seen = set()
        for px, py in points:
            rx, ry = self._resolve_obstacle_overlap(px, py, radius, scene_id)
            key = (round(rx, 1), round(ry, 1))
            if key in seen or not self._room_nav_point_clear(scene_id, rx, ry, radius):
                continue
            seen.add(key)
            clean.append((rx, ry))
        return clean

    def _invalidate_room_nav_cache(self, scene_id=None):
        if scene_id is None:
            self.room_nav_cache.clear()
            return
        for key in list(self.room_nav_cache.keys()):
            if key[0] == scene_id:
                self.room_nav_cache.pop(key, None)

    def _room_nav_graph(self, scene_id, radius):
        key = (scene_id, round(radius, 1))
        cached = self.room_nav_cache.get(key)
        if cached:
            return cached
        nodes = self._room_nav_points(scene_id, radius)
        adj = [[] for _ in nodes]
        connected = set()
        for i, point in enumerate(nodes):
            ax, ay = point
            candidates = heapq.nsmallest(
                ROOM_NAV_NEIGHBOR_LIMIT,
                (
                    (math.hypot(nodes[j][0] - ax, nodes[j][1] - ay), j, nodes[j][0], nodes[j][1])
                    for j in range(len(nodes))
                    if j != i
                ),
            )
            for step, j, bx, by in candidates:
                edge = (min(i, j), max(i, j))
                if edge in connected:
                    continue
                if self._segment_blocked(ax, ay, bx, by, radius=radius, scene=scene_id):
                    continue
                connected.add(edge)
                adj[i].append((j, step))
                adj[j].append((i, step))
        cached = (nodes, adj)
        self.room_nav_cache[key] = cached
        return cached

    def _room_visibility_path(self, scene_id, zombie, target, path_radius):
        start = (zombie["x"], zombie["y"])
        goal = (target["x"], target["y"])
        nodes, adj = self._room_nav_graph(scene_id, path_radius)
        start_neighbors = []
        goal_neighbors = {}
        endpoint_candidate_count = min(len(nodes), ROOM_PATH_ENDPOINT_NEIGHBORS * 3)
        start_order = heapq.nsmallest(
            endpoint_candidate_count,
            (
                (math.hypot(wx - start[0], wy - start[1]), idx, wx, wy)
                for idx, (wx, wy) in enumerate(nodes)
            ),
        )
        for step, idx, wx, wy in start_order:
            if not self._segment_blocked(start[0], start[1], wx, wy, radius=path_radius, scene=scene_id):
                start_neighbors.append((idx, step))
                if len(start_neighbors) >= ROOM_PATH_ENDPOINT_NEIGHBORS:
                    break
        goal_order = heapq.nsmallest(
            endpoint_candidate_count,
            (
                (math.hypot(goal[0] - wx, goal[1] - wy), idx, wx, wy)
                for idx, (wx, wy) in enumerate(nodes)
            ),
        )
        for step, idx, wx, wy in goal_order:
            if not self._segment_blocked(wx, wy, goal[0], goal[1], radius=path_radius, scene=scene_id):
                goal_neighbors[idx] = step
                if len(goal_neighbors) >= ROOM_PATH_ENDPOINT_NEIGHBORS:
                    break
        if not start_neighbors or not goal_neighbors:
            return None
        goal_node = -1
        start_node = -2
        dist_to = {start_node: 0.0}
        prev = {}
        heap = [(0.0, start_node)]
        visited = set()
        while heap:
            cost, idx = heapq.heappop(heap)
            if idx in visited:
                continue
            visited.add(idx)
            if idx == goal_node:
                path = [goal]
                cur = idx
                while cur in prev:
                    cur = prev[cur]
                    if cur >= 0:
                        path.append(nodes[cur])
                path.append(start)
                path.reverse()
                return path
            if idx == start_node:
                neighbors = start_neighbors
            else:
                neighbors = list(adj[idx])
                if idx in goal_neighbors:
                    neighbors.append((goal_node, goal_neighbors[idx]))
            for next_idx, step in neighbors:
                new_cost = cost + step
                if new_cost >= dist_to.get(next_idx, float("inf")):
                    continue
                dist_to[next_idx] = new_cost
                prev[next_idx] = idx
                heapq.heappush(heap, (new_cost, next_idx))
        return None


    def _jitter_floor_point(self, point, jitter=MAZE_SAFE_JITTER):
        x = point[0] + random.uniform(-jitter, jitter)
        y = point[1] + random.uniform(-jitter, jitter)
        return clamp(x, PLAYER_R, MAP_W - PLAYER_R), clamp(y, PLAYER_R, MAP_H - PLAYER_R)

    def _floor_spawn(self, min_player_dist=0, max_player_dist=None, near=None, far_from_spawn=False):
        points = self.floor_points or [(MAP_W // 2, MAP_H // 2)]
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

    def _entity_scene(self, entity):
        return entity.get("scene") or SCENE_MAIN

    def _scene_def(self, scene_id):
        if not scene_id or scene_id == SCENE_MAIN:
            return {
                "id": SCENE_MAIN,
                "name": "设施楼层",
                "mw": MAP_W,
                "mh": MAP_H,
                "obs": self.obstacles,
                "features": self.map_features,
            }
        return self.room_scenes.get(scene_id) or {
            "id": SCENE_MAIN,
            "name": "设施楼层",
            "mw": MAP_W,
            "mh": MAP_H,
            "obs": self.obstacles,
            "features": self.map_features,
        }

    def _scene_payload(self, scene_id):
        scene = self._scene_def(scene_id)
        is_main = scene.get("id") == SCENE_MAIN
        return {
            "scene": scene.get("id", SCENE_MAIN),
            "sceneName": scene.get("name", "设施楼层"),
            "mw": scene.get("mw", MAP_W),
            "mh": scene.get("mh", MAP_H),
            "dynamicAoi": self._dynamic_aoi_radius(scene.get("id", SCENE_MAIN)),
            "obs": self.obstacles if is_main else scene.get("obs", []),
            "features": self.map_features if is_main else scene.get("features", []),
            "exits": self._extractions_snapshot() if is_main else [],
            "mission": self._mission_snapshot() if is_main else None,
            "obj": self._objective_snapshot(),
        }

    def _room_by_id(self, room_id):
        for feature in self.map_features:
            if feature.get("kind") == "room" and feature.get("id") == room_id:
                return feature
        return None

    def _room_for_scene(self, scene_id):
        scene = self.room_scenes.get(scene_id or "")
        return self._room_by_id(scene.get("room_id", "")) if scene else None

    def _emit_scene_change(self, sid, reason="scene"):
        player = self.players.get(sid)
        if not player:
            return
        payload = self._scene_payload(self._entity_scene(player))
        payload.update({
            "pid": sid,
            "reason": reason,
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
        })
        self._emit_to("scene_change", payload, [sid])

    def refresh_scene(self, sid):
        if sid not in self.players:
            return False
        self._emit_scene_change(sid, reason="refresh")
        return True

    def _scene_has_players(self, scene_id):
        if not scene_id:
            return False
        return any(self._entity_scene(player) == scene_id for player in self.players.values())

    def _sweep_empty_room_scene(self, scene_id):
        if not scene_id or scene_id == SCENE_MAIN or self._scene_has_players(scene_id):
            return
        self.pending_fog_spawns = [
            entry for entry in self.pending_fog_spawns
            if entry.get("scene") != scene_id
        ]
        for entities in (self.zombies, self.bullets, self.items):
            for eid, entity in list(entities.items()):
                if self._entity_scene(entity) == scene_id:
                    entities.pop(eid, None)

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

    def _near_obstacles(self, x, y, radius, scene=SCENE_MAIN):
        if scene and scene != SCENE_MAIN:
            yield from self._scene_def(scene).get("obs", [])
            return
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

    def _overlaps_obstacle(self, x, y, radius, scene=SCENE_MAIN):
        return any(
            circ_rect(x, y, radius, obstacle["x"], obstacle["y"], obstacle["w"], obstacle["h"])
            for obstacle in self._near_obstacles(x, y, radius + MAZE_WALL + 4, scene=scene)
        )

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

    def _move_col_once(self, x, y, radius, dx, dy, scene=SCENE_MAIN):
        scene_def = self._scene_def(scene)
        mw = scene_def.get("mw", MAP_W)
        mh = scene_def.get("mh", MAP_H)
        nx = max(radius, min(mw - radius, x + dx))
        ny = max(radius, min(mh - radius, y + dy))
        near = list(self._near_obstacles(nx, ny, radius + MAZE_WALL + 4, scene=scene))

        def _hit(tx, ty):
            return any(circ_rect(tx, ty, radius, o["x"], o["y"], o["w"], o["h"]) for o in near)

        if _hit(nx, ny):
            if not _hit(nx, y):
                ny = y
            elif not _hit(x, ny):
                nx = x
            else:
                nx, ny = x, y
        return self._resolve_obstacle_overlap(nx, ny, radius, scene)

    def _resolve_obstacle_overlap(self, x, y, radius, scene=SCENE_MAIN):
        scene_def = self._scene_def(scene)
        mw = scene_def.get("mw", MAP_W)
        mh = scene_def.get("mh", MAP_H)
        cx = max(radius, min(mw - radius, x))
        cy = max(radius, min(mh - radius, y))
        resolved = False
        for _ in range(3):
            moved = False
            for obstacle in self._near_obstacles(cx, cy, radius + MAZE_WALL + 4, scene=scene):
                ox, oy = obstacle["x"], obstacle["y"]
                ow, oh = obstacle["w"], obstacle["h"]
                nearest_x = clamp(cx, ox, ox + ow)
                nearest_y = clamp(cy, oy, oy + oh)
                dx = cx - nearest_x
                dy = cy - nearest_y
                dist_sq = dx * dx + dy * dy
                if dist_sq >= radius * radius:
                    continue
                if dist_sq > 0.0001:
                    dist = math.sqrt(dist_sq)
                    push = radius - dist + 0.35
                    cx += dx / dist * push
                    cy += dy / dist * push
                else:
                    distances = (
                        (abs(cx - ox), ox - radius - 0.35, cy),
                        (abs((ox + ow) - cx), ox + ow + radius + 0.35, cy),
                        (abs(cy - oy), cx, oy - radius - 0.35),
                        (abs((oy + oh) - cy), cx, oy + oh + radius + 0.35),
                    )
                    _, cx, cy = min(distances, key=lambda item: item[0])
                cx = max(radius, min(mw - radius, cx))
                cy = max(radius, min(mh - radius, cy))
                moved = True
                resolved = True
            if not moved:
                break
        if self._overlaps_obstacle(cx, cy, radius, scene):
            candidates = []
            for obstacle in self._near_obstacles(cx, cy, radius + MAZE_WALL + 4, scene=scene):
                ox, oy = obstacle["x"], obstacle["y"]
                ow, oh = obstacle["w"], obstacle["h"]
                safe_left = ox - radius - 0.35
                safe_right = ox + ow + radius + 0.35
                safe_top = oy - radius - 0.35
                safe_bottom = oy + oh + radius + 0.35
                mid_x = clamp(cx, ox, ox + ow)
                mid_y = clamp(cy, oy, oy + oh)
                candidates.extend((
                    (safe_left, mid_y),
                    (safe_right, mid_y),
                    (mid_x, safe_top),
                    (mid_x, safe_bottom),
                    (safe_left, safe_top),
                    (safe_left, safe_bottom),
                    (safe_right, safe_top),
                    (safe_right, safe_bottom),
                ))
            valid = []
            for px, py in candidates:
                px = max(radius, min(mw - radius, px))
                py = max(radius, min(mh - radius, py))
                if not self._overlaps_obstacle(px, py, radius, scene):
                    valid.append((px, py))
            if valid:
                cx, cy = min(valid, key=lambda point: (point[0] - x) ** 2 + (point[1] - y) ** 2)
                resolved = True
        if resolved:
            self._overlap_resolves_this_tick += 1
        return cx, cy

    def move_col(self, x, y, radius, dx, dy, scene=SCENE_MAIN):
        dist = math.hypot(dx, dy)
        if dist <= 0.01:
            return self._resolve_obstacle_overlap(x, y, radius, scene)
        steps = max(1, math.ceil(dist / MOVE_COLLISION_STEP))
        step_x = dx / steps
        step_y = dy / steps
        cx, cy = x, y
        for _ in range(steps):
            nx, ny = self._move_col_once(cx, cy, radius, step_x, step_y, scene=scene)
            if abs(nx - cx) < 0.001 and abs(ny - cy) < 0.001:
                break
            cx, cy = nx, ny
        return cx, cy

    def _room_spawn(self, scene_id, near=None, min_player_dist=0, max_player_dist=None, jitter=42, preferred_index=None):
        scene = self._scene_def(scene_id)
        points = scene.get("zombie_points") or [
            (scene.get("mw", ROOM_W) - 240, 190),
            (scene.get("mw", ROOM_W) - 260, scene.get("mh", ROOM_H) - 210),
            (scene.get("mw", ROOM_W) * 0.62, scene.get("mh", ROOM_H) * 0.5),
        ]
        if preferred_index is not None and points:
            start = int(preferred_index) % len(points)
            points = points[start:] + points[:start]
        candidates = []
        for point in points:
            if near is not None:
                d = math.hypot(point[0] - near["x"], point[1] - near["y"])
                if d < min_player_dist:
                    continue
                if max_player_dist is not None and d > max_player_dist:
                    continue
            candidates.append(point)
        if not candidates:
            candidates = points
        for _ in range(30):
            if preferred_index is None:
                px, py = random.choice(candidates)
            else:
                px, py = candidates[_ % len(candidates)]
            x = clamp(px + random.uniform(-jitter, jitter), PLAYER_R, scene.get("mw", ROOM_W) - PLAYER_R)
            y = clamp(py + random.uniform(-jitter, jitter), PLAYER_R, scene.get("mh", ROOM_H) - PLAYER_R)
            if any(circ_rect(x, y, PLAYER_R + 4, o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(x, y, PLAYER_R + MAZE_WALL + 4, scene=scene_id)):
                continue
            return x, y
        return random.choice(candidates)

    def safe_spawn(self, scene=SCENE_MAIN):
        if scene and scene != SCENE_MAIN:
            scene_def = self._scene_def(scene)
            loot = scene_def.get("loot", {"x": 260, "y": 180, "w": ROOM_W - 520, "h": ROOM_H - 360})
            return (
                random.uniform(loot["x"], loot["x"] + loot["w"]),
                random.uniform(loot["y"], loot["y"] + loot["h"]),
            )
        return self._floor_spawn(min_player_dist=190, far_from_spawn=True)

    def safe_player_spawn(self):
        return self._jitter_floor_point(self.spawn_point, jitter=70)

    def safe_zombie_spawn(self, pressure=False, scene=SCENE_MAIN):
        alive = [
            p for p in self.players.values()
            if not p.get("dead") and not p.get("paused") and self._entity_scene(p) == scene
        ]
        if scene and scene != SCENE_MAIN:
            near = random.choice(alive) if pressure and alive else None
            return self._room_spawn(
                scene,
                near=near,
                min_player_dist=130 if near else 0,
                max_player_dist=640 if near else None,
            )
        if pressure and alive:
            target = random.choice(alive)
            return self._floor_spawn(
                min_player_dist=PRESSURE_SPAWN_MIN_DIST,
                max_player_dist=PRESSURE_SPAWN_MAX_DIST,
                near=target,
            )
        return self._floor_spawn(min_player_dist=430, far_from_spawn=True)

    def safe_fog_spawn(self, origin=None, scene=SCENE_MAIN, spawn_index=None):
        if origin and origin.get("scene"):
            scene = origin.get("scene")
        if scene and scene != SCENE_MAIN:
            return self._room_spawn(
                scene,
                near=origin,
                min_player_dist=260 if origin else 0,
                max_player_dist=None,
                jitter=34,
                preferred_index=spawn_index,
            )
        if origin:
            return self._floor_spawn(
                min_player_dist=max(240, FOG_WAVE_MIN_DIST * 0.72),
                max_player_dist=max(520, FOG_WAVE_MAX_DIST * 0.86),
                near=origin,
            )
        alive = [
            p for p in self.players.values()
            if not p.get("dead") and not p.get("paused") and self._entity_scene(p) == scene
        ]
        if alive:
            target = random.choice(alive)
            return self._floor_spawn(
                min_player_dist=FOG_WAVE_MIN_DIST,
                max_player_dist=FOG_WAVE_MAX_DIST,
                near=target,
            )
        return self.safe_zombie_spawn(pressure=True, scene=scene)

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

    def _pressure_zombie_type(self, urgent=False):
        if not urgent:
            return self._zombie_type_for_wave()
        roles = (
            ("runner", 1, 6),
            ("crawler", 1, 4),
            ("shade", 1, 5),
            ("brute", 1, 3),
            ("toxic", 1, 4),
            ("armored", 2, 2),
            ("leaper", 2, 3),
            ("stalker", 2, 4),
            ("spitter", 2, 3),
            ("screamer", 3, 2),
            ("bloater", 3, 1),
            ("warden", 4, 1),
        )
        choices = []
        weights = []
        for ztype, unlock, weight in roles:
            if self.wave >= unlock:
                choices.append(ztype)
                weights.append(weight + max(0, self.wave - unlock) * 0.35)
        if not choices:
            return self._zombie_type_for_wave()
        return random.choices(choices, weights=weights)[0]

    def _next_spawn_budget_source(self, allow_infection_source=False):
        if self.wave_remaining > 0:
            return "wave"
        if allow_infection_source and self.infection_source_remaining > 0:
            return "infection"
        return None

    def _consume_spawn_budget(self, source):
        if source == "wave":
            self.wave_remaining = max(0, self.wave_remaining - 1)
        elif source == "infection":
            self.infection_source_remaining = max(0, self.infection_source_remaining - 1)

    def _pending_fog_spawn_count(self):
        return len(getattr(self, "pending_fog_spawns", []))

    def _queue_fog_spawns(
        self,
        count,
        now,
        reason="director",
        urgent=True,
        origin=None,
        scene=SCENE_MAIN,
        independent=False,
    ):
        if count <= 0 or len(self.zombies) + self._pending_fog_spawn_count() >= MAX_ZOMBIES:
            return 0, 0
        if independent:
            budget = min(count, MAX_ZOMBIES - len(self.zombies) - self._pending_fog_spawn_count())
        else:
            available = self.wave_remaining + self.infection_source_remaining
            if available <= 0:
                return 0, 0
            budget = min(count, available, MAX_ZOMBIES - len(self.zombies) - self._pending_fog_spawn_count())
        queued = 0
        source_count = 0
        origin_payload = dict(origin) if origin else None
        for index in range(max(0, budget)):
            source = "room" if independent else self._next_spawn_budget_source(allow_infection_source=True)
            if not source:
                break
            if not independent:
                self._consume_spawn_budget(source)
            if source == "infection":
                source_count += 1
            self.pending_fog_spawns.append({
                "scene": scene or SCENE_MAIN,
                "origin": origin_payload,
                "ztype": self._fog_zombie_type(index),
                "source": source,
                "rally_until": now + 2.2,
                "reason": reason,
                "spawn_index": index,
            })
            queued += 1
        return queued, source_count

    def _process_pending_fog_spawns(self, now):
        if not self.pending_fog_spawns:
            return 0
        spawn_now = []
        keep = []
        scene_budget_used = {}
        for entry in self.pending_fog_spawns:
            scene = entry.get("scene", SCENE_MAIN)
            limit = FOG_SPAWNS_PER_TICK if scene == SCENE_MAIN else ROOM_FOG_SPAWNS_PER_TICK
            if len(self.zombies) + len(spawn_now) >= MAX_ZOMBIES:
                keep.append(entry)
                continue
            if scene_budget_used.get(scene, 0) >= limit:
                keep.append(entry)
                continue
            scene_budget_used[scene] = scene_budget_used.get(scene, 0) + 1
            spawn_now.append(entry)
        self.pending_fog_spawns = keep

        spawned = 0
        for entry in spawn_now:
            ztype = entry.get("ztype") or self._pressure_zombie_type(urgent=True)
            self._prewarm_room_zombie_nav(entry.get("scene", SCENE_MAIN), ztype)
            x, y = self.safe_fog_spawn(
                origin=entry.get("origin"),
                scene=entry.get("scene", SCENE_MAIN),
                spawn_index=entry.get("spawn_index"),
            )
            zid = self.spawn_zombie(
                x=x,
                y=y,
                ztype=ztype,
                emit=False,
                pressure=True,
                scene=entry.get("scene", SCENE_MAIN),
            )
            if not zid:
                continue
            zombie = self.zombies[zid]
            zombie["rally_until"] = max(zombie.get("rally_until", 0), entry.get("rally_until", now + 1.2))
            if entry.get("source") == "infection":
                zombie["source"] = "infection"
            elif entry.get("source") == "room":
                zombie["source"] = "room"
            spawned += 1
        return spawned

    def _spawn_pressure_pack(
        self,
        count,
        now,
        urgent=False,
        allow_infection_source=False,
        origin=None,
        scene=None,
        independent=False,
    ):
        if count <= 0 or len(self.zombies) >= MAX_ZOMBIES:
            return 0
        if independent:
            budget = min(count, MAX_ZOMBIES - len(self.zombies))
        else:
            available = self.wave_remaining + (self.infection_source_remaining if allow_infection_source else 0)
            if available <= 0:
                return 0
            budget = min(count, available, MAX_ZOMBIES - len(self.zombies))
        spawned = 0
        spawned_from_source = 0
        spawn_scene = scene or (origin.get("scene") if origin else None)
        if not spawn_scene:
            alive = [p for p in self.players.values() if not p.get("dead") and not p.get("paused")]
            spawn_scene = self._entity_scene(random.choice(alive)) if alive else SCENE_MAIN
        for _ in range(max(0, budget)):
            source = "room" if independent else self._next_spawn_budget_source(allow_infection_source)
            if not source:
                break
            x = y = None
            if origin:
                x, y = self.safe_fog_spawn(origin=origin, scene=spawn_scene)
            ztype = self._pressure_zombie_type(urgent=urgent)
            self._prewarm_room_zombie_nav(spawn_scene, ztype)
            zid = self.spawn_zombie(
                x=x,
                y=y,
                ztype=ztype,
                emit=False,
                pressure=True,
                scene=spawn_scene,
            )
            if not zid:
                continue
            if not independent:
                self._consume_spawn_budget(source)
            spawned += 1
            if source == "infection":
                spawned_from_source += 1
            zombie = self.zombies[zid]
            if urgent:
                zombie["rally_until"] = max(zombie.get("rally_until", 0), now + 1.2)
            if source == "infection":
                zombie["source"] = "infection"
            elif source == "room":
                zombie["source"] = "room"
        if spawned_from_source and spawn_scene == SCENE_MAIN:
            self.fog_active_until = max(self.fog_active_until, now + 3.2)
        return spawned

    def _fog_zombie_type(self, index=0):
        scripted = ("shade", "runner", "crawler", "toxic", "stalker", "spitter", "shade", "brute")
        if index < len(scripted):
            return scripted[index]
        roles = (
            ("shade", 1, 8),
            ("runner", 1, 5),
            ("crawler", 1, 4),
            ("toxic", 1, 3),
            ("brute", 1, 2),
            ("armored", 2, 2),
            ("leaper", 2, 3),
            ("stalker", 2, 4),
            ("spitter", 2, 3),
            ("screamer", 3, 2),
            ("bloater", 3, 1),
            ("warden", 4, 1),
        )
        choices = []
        weights = []
        for ztype, unlock, weight in roles:
            if self.wave >= unlock:
                choices.append(ztype)
                weights.append(weight + max(0, self.wave - unlock) * 0.3)
        return random.choices(choices, weights=weights)[0] if choices else "shade"

    def _fog_scene(self, reason):
        scenes = {
            "medbay": {
                "name": "病房血雾",
                "color": "#ff7a8a",
                "duration": 5.6,
                "bonus": -1,
            },
            "generator": {
                "name": "机房断电警报",
                "color": "#66d9ff",
                "duration": 5.2,
                "bonus": 2,
            },
            "lab": {
                "name": "样本库污染雾",
                "color": "#b7ff47",
                "duration": 6.2,
                "bonus": 3,
            },
            "armory": {
                "name": "仓库警报",
                "color": "#ffc247",
                "duration": 5.0,
                "bonus": 2,
            },
            "archive": {
                "name": "档案室回声",
                "color": "#aee6ff",
                "duration": 5.3,
                "bonus": 2,
            },
            "security": {
                "name": "安保封锁",
                "color": "#d98cff",
                "duration": 5.8,
                "bonus": 3,
            },
            "morgue": {
                "name": "停尸间尸雾",
                "color": "#b7ff47",
                "duration": 6.1,
                "bonus": 4,
            },
            "terminal": {
                "name": "终端回声",
                "color": "#d98cff",
                "duration": 5.4,
                "bonus": 3,
            },
            "extraction": {
                "name": "撤离封锁",
                "color": "#ff4d5f",
                "duration": 6.0,
                "bonus": 4,
            },
            "silence": {
                "name": "静默雾袭",
                "color": "#d6eceb",
                "duration": 4.8,
                "bonus": 0,
            },
            "director": {
                "name": "雾袭",
                "color": "#d6eceb",
                "duration": 4.8,
                "bonus": 0,
            },
        }
        return scenes.get(reason, scenes["director"])

    def _prewarm_room_zombie_nav(self, scene_id, ztype):
        if not scene_id or scene_id == SCENE_MAIN:
            return
        meta = ZOMBIE_TYPES.get(ztype, ZOMBIE_TYPES["walker"])
        self._room_nav_graph(scene_id, meta.get("radius", 16) + 8)

    def _trigger_fog_wave(self, now, reason="director", force=False, origin=None, scene=None):
        if len(self.zombies) >= MAX_ZOMBIES:
            return 0
        spawn_scene = scene or (origin.get("scene") if origin else None) or SCENE_MAIN
        indoor = spawn_scene != SCENE_MAIN
        if not force and not indoor and now < self.next_fog_wave_at:
            return 0
        alive_count = max(
            1,
            sum(
                1 for player in self.players.values()
                if not player.get("dead") and self._entity_scene(player) == spawn_scene
            ),
        )
        fog_scene = self._fog_scene(reason)
        if indoor:
            pressure_bonus = 1 if reason in ROOM_FOG_PRESSURE_BONUS_REASONS else 0
            desired_count = ROOM_FOG_WAVE_BASE + min(2, max(0, self.wave - 1) // 2) + pressure_bonus
            max_count = ROOM_FOG_WAVE_MAX
        else:
            desired_count = (
                FOG_WAVE_COUNT_BASE
                + alive_count * FOG_WAVE_COUNT_PER_PLAYER
                + min(10, self.wave * 2)
                + fog_scene.get("bonus", 0)
            )
            max_count = FOG_WAVE_MAX
        available_budget = (
            MAX_ZOMBIES - len(self.zombies) - self._pending_fog_spawn_count()
            if indoor
            else self.wave_remaining + self.infection_source_remaining
        )
        count = min(
            max_count,
            desired_count,
            available_budget,
            MAX_ZOMBIES - len(self.zombies) - self._pending_fog_spawn_count(),
        )
        if count <= 0:
            return 0
        spawn_origin = None
        if origin:
            spawn_origin = {"x": origin["x"], "y": origin["y"], "scene": spawn_scene}
        queued, spawned_from_source = self._queue_fog_spawns(
            count,
            now,
            reason=reason,
            urgent=True,
            origin=spawn_origin,
            scene=spawn_scene,
            independent=indoor,
        )
        if not queued:
            return 0
        duration = fog_scene.get("duration", 4.8)
        if not indoor:
            cooldown = max(8.0, FOG_WAVE_COOLDOWN - min(6.0, self.wave * 0.7))
            self.next_fog_wave_at = now + cooldown
            self.fog_active_until = now + duration
        if spawn_origin:
            event_x = spawn_origin["x"]
            event_y = spawn_origin["y"]
        else:
            viewers = [
                player for player in self.players.values()
                if not player.get("dead") and self._entity_scene(player) == spawn_scene
            ]
            target = random.choice(viewers) if viewers else None
            event_x = target["x"] if target else self.spawn_point[0]
            event_y = target["y"] if target else self.spawn_point[1]
        payload = {
            "reason": reason,
            "scene": fog_scene.get("name", "雾袭"),
            "sceneId": spawn_scene,
            "count": queued,
            "wave": self.wave,
            "duration": duration,
            "x": round(event_x, 1),
            "y": round(event_y, 1),
            "spawnX": round(event_x, 1),
            "spawnY": round(event_y, 1),
            "col": fog_scene.get("color", "#d6eceb"),
            "sourceCount": spawned_from_source,
            "sourceRemaining": self.infection_source_remaining,
        }
        if origin:
            self._emit_near("fog_wave", payload, event_x, event_y, radius=EVENT_INTEREST_RADIUS * 1.2, scene=spawn_scene)
        else:
            self._emit_near("fog_wave", payload, event_x, event_y, radius=max(MAP_W, MAP_H, ROOM_W, ROOM_H) * 2, scene=spawn_scene)
        return queued

    def spawn_zombie(self, x=None, y=None, ztype=None, emit=True, pressure=False, scene=SCENE_MAIN):
        if len(self.zombies) >= MAX_ZOMBIES:
            return None
        if x is None:
            x, y = self.safe_zombie_spawn(pressure=pressure, scene=scene)
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
            "slam_cd": 0,
            "phase": 0,
            "scream_cd": 0,
            "rally_until": 0,
            "path": None,
            "path_target": None,
            "path_goal": None,
            "path_time": 0,
            "path_idx": 1,
            "scene": scene or SCENE_MAIN,
        }
        if emit:
            self._emit_near("z_spawn", self._zombie_event(zid, self.zombies[zid]), x, y, scene=scene or SCENE_MAIN)
        return zid

    def spawn_item(self, x=None, y=None, item_type=None, emit=True, scene=SCENE_MAIN, force=False):
        if len(self.items) >= self._max_items and not force:
            return None
        if x is None:
            x, y = self.safe_spawn(scene=scene)
        if any(pt_in_rect(x, y, o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(x, y, ITEM_R + MAZE_WALL, scene=scene)):
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
            "scene": scene or SCENE_MAIN,
        }
        if emit:
            self._emit_near("i_spawn", self._item_event(iid, self.items[iid]), x, y, scene=scene or SCENE_MAIN)
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
        return player.get("paused") or now < player.get("protect_until", 0) or now < player.get("shield_until", 0)

    def _check_level_up(self, player):
        leveled = False
        while player.get("xp", 0) >= player.get("level", 1) * LEVEL_XP_BASE:
            player["xp"] -= player["level"] * LEVEL_XP_BASE
            player["level"] += 1
            player["max_hp"] = (
                PLAYER_MAX_HP
                + min(45, (player["level"] - 1) * 5)
                + talent_level(player, "vitality") * 12
            )
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
            player["levelup_boost_until"] = now + 2.0
            self._emit("level_up", {
                "pid": sid,
                "level": player["level"],
                "x": round(player["x"], 1),
                "y": round(player["y"], 1),
                "col": player["color"],
                "sceneId": self._entity_scene(player),
                "_targets": [sid],
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

    def _weapon_mag_size(self, player, weapon_id=None):
        wid = weapon_id or player.get("weapon_id", "pistol")
        base = weapon_meta(wid)["mag_size"]
        bonus = max(0, player.get("weapon_level", 1) - 1)
        capacity_bonus = talent_level(player, "capacity") * 2
        if wid == "launcher":
            return base + min(2, bonus // 3) + min(3, capacity_bonus)
        if wid == "shotgun":
            return base + min(4, bonus // 2) + capacity_bonus
        return base + bonus * 2 + capacity_bonus

    def _weapon_state(self, player, weapon_id=None):
        wid = weapon_id or player.get("weapon_id", "pistol")
        weapons = player.setdefault("weapons", {})
        if wid not in weapons:
            weapons[wid] = {"ammo": self._weapon_mag_size(player, wid)}
        weapons[wid]["ammo"] = min(weapons[wid].get("ammo", 0), self._weapon_mag_size(player, wid))
        return weapons[wid]

    def _sync_weapon_fields(self, player, prefer_player=True):
        wid = player.get("weapon_id", "pistol")
        if wid not in WEAPON_TYPES:
            wid = "pistol"
            player["weapon_id"] = wid
        state = self._weapon_state(player, wid)
        player["mag_size"] = self._weapon_mag_size(player, wid)
        if prefer_player and "ammo" in player:
            state["ammo"] = min(player["mag_size"], max(0, int(player.get("ammo", 0))))
        player["ammo"] = min(player["mag_size"], max(0, state.get("ammo", player["mag_size"])))
        state["ammo"] = player["ammo"]
        player["current_reserve"] = self._ammo_reserve(player, ammo_type_for_weapon(wid))
        return wid, weapon_meta(wid), state

    def _unlocked_weapon_ids(self, player):
        weapons = player.setdefault("weapons", {"pistol": {"ammo": self._weapon_mag_size(player, "pistol")}})
        ordered = [wid for wid in WEAPON_ORDER if wid in weapons]
        return ordered or ["pistol"]

    def _unlock_weapon(self, player, weapon_id, now, notify=True):
        if weapon_id not in WEAPON_TYPES:
            return False
        weapons = player.setdefault("weapons", {})
        unlocked = weapon_id not in weapons
        weapons.setdefault(weapon_id, {"ammo": self._weapon_mag_size(player, weapon_id)})
        meta = weapon_meta(weapon_id)
        ammo_type = meta.get("ammo_type", "pistol")
        reserve_bonus = meta.get("unlock_reserve", 0) if unlocked else max(1, meta.get("unlock_reserve", 0) // 3)
        self._add_ammo_reserve(player, ammo_type, reserve_bonus)
        if weapon_id == player.get("weapon_id", "pistol"):
            self._sync_weapon_fields(player)
        if unlocked and notify:
            payload = {
                "pid": player["id"],
                "weapon": weapon_id,
                "weaponName": meta["name"],
                "weapons": self._unlocked_weapon_ids(player),
                "ammo": player.get("ammo", 0),
                "col": meta.get("color", player.get("color", "#dce7f1")),
                "x": round(player["x"], 1),
                "y": round(player["y"], 1),
            }
            payload.update(self._current_ammo_payload(player, ammo_type))
            self._emit_to("weapon_unlock", payload, [player["id"]])
        return unlocked

    def _switch_weapon(self, sid, player, weapon_id, now, notify=True):
        if not weapon_id or weapon_id not in player.setdefault("weapons", {}):
            return False
        current = player.get("weapon_id", "pistol")
        self._weapon_state(player, current)["ammo"] = player.get("ammo", 0)
        if current == weapon_id:
            self._sync_weapon_fields(player)
            return False
        player["weapon_id"] = weapon_id
        player["reload_until"] = 0
        wid, meta, _ = self._sync_weapon_fields(player, prefer_player=False)
        if notify:
            payload = {
                "pid": sid,
                "weapon": wid,
                "weaponName": meta["name"],
                "ammo": player.get("ammo", 0),
                "magSize": player.get("mag_size", meta["mag_size"]),
                "weapons": self._unlocked_weapon_ids(player),
                "col": meta.get("color", player.get("color", "#dce7f1")),
            }
            payload.update(self._current_ammo_payload(player))
            self._emit_to("weapon_switch", payload, [sid])
        return True

    def _apply_item(self, sid, item, now):
        player = self.players.get(sid)
        if not player or player.get("dead"):
            return
        typ = item["type"]
        item_meta = ITEM_TYPES.get(typ, {})
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
                "sceneId": self._entity_scene(item),
            })
        elif typ == "rapid":
            player["rapid_until"] = now + 7.5
        elif typ == "spread":
            player["spread_until"] = now + 7.0
        elif typ == "shield":
            affected = 0
            player_scene = self._entity_scene(player)
            for teammate in self.players.values():
                if teammate.get("dead"):
                    continue
                if self._entity_scene(teammate) != player_scene:
                    continue
                if math.hypot(teammate["x"] - player["x"], teammate["y"] - player["y"]) <= 380:
                    teammate["shield_until"] = max(teammate.get("shield_until", 0), now + 5.8)
                    affected += 1
            item["amount"] = max(1, affected)
        elif typ == "medkit":
            player["hp"] = min(player["max_hp"], player.get("hp", player["max_hp"]) + 42)
        elif typ == "ammo" or item_meta.get("ammo_type"):
            ammo_type = item_meta.get("ammo_type") or ammo_type_for_weapon(player.get("weapon_id", "pistol"))
            if typ == "ammo" and ammo_type == "explosive":
                unlocked = set(self._unlocked_weapon_ids(player))
                candidates = [ammo_type_for_weapon(wid) for wid in self._unlocked_weapon_ids(player) if wid != "launcher"]
                ammo_type = random.choice(candidates or ["pistol"])
            lo, hi = AMMO_PICKUP_BY_TYPE.get(ammo_type, (AMMO_PICKUP_MIN, AMMO_PICKUP_MAX))
            amount = random.randint(lo, hi)
            self._add_ammo_reserve(player, ammo_type, amount)
            self._sync_weapon_fields(player)
            item["amount"] = amount
            item["ammo_type"] = ammo_type
        elif typ == "parts":
            amount = random.randint(MATERIAL_PICKUP_MIN, MATERIAL_PICKUP_MAX)
            player["materials"] = player.get("materials", 0) + amount
            item["amount"] = amount
        elif typ == "lore":
            player["lore"] = player.get("lore", 0) + 1
            item["amount"] = 1
            file_text = CASE_FILES[(player["lore"] - 1) % len(CASE_FILES)]
            self._emit_to("lore_found", {
                "pid": sid,
                "count": player["lore"],
                "text": file_text,
                "col": item["color"],
                "sceneId": self._entity_scene(item),
            }, [sid])
        elif typ == "adrenaline":
            player["adrenaline_until"] = now + 8.0
        elif typ == "damage_boost":
            player["damage_boost_until"] = now + 8.0
        elif typ == "nuke":
            self._nuke(sid, item["x"], item["y"], now)
        elif typ.startswith("weapon_"):
            weapon_id = item_meta.get("weapon")
            unlocked = self._unlock_weapon(player, weapon_id, now)
            if weapon_id:
                self._switch_weapon(sid, player, weapon_id, now)
            item["amount"] = 1 if unlocked else 10
        elif typ == "vehicle":
            player["vehicle_until"] = now + VEHICLE_SECONDS
            player["vehicle_ram_cd"] = 0
            player["vehicle_end_notified"] = False
            item["amount"] = int(VEHICLE_SECONDS)
            self._emit_to("vehicle_start", {
                "pid": sid,
                "duration": VEHICLE_SECONDS,
                "speedMult": VEHICLE_SPEED_MULT,
                "x": round(player["x"], 1),
                "y": round(player["y"], 1),
                "col": item["color"],
            }, [sid])
        payload = {
            "pid": sid,
            "iid": item["id"],
            "type": typ,
            "name": item["name"],
            "icon": item["icon"],
            "col": item["color"],
            "x": round(item["x"], 1),
            "y": round(item["y"], 1),
            "amount": item.get("amount", 1),
            "ammo": player.get("ammo", 0),
            "materials": player.get("materials", 0),
            "lore": player.get("lore", 0),
            "weaponLevel": player.get("weapon_level", 1),
            "weapon": player.get("weapon_id", "pistol"),
            "weaponName": weapon_meta(player.get("weapon_id", "pistol"))["name"],
            "weapons": self._unlocked_weapon_ids(player),
            "vehicle": now < player.get("vehicle_until", 0),
        }
        payload.update(self._current_ammo_payload(player, item.get("ammo_type")))
        self._emit_near("item_pick", payload, item["x"], item["y"], include=sid, scene=item.get("scene", SCENE_MAIN))

    def _nuke(self, sid, x, y, now):
        player = self.players.get(sid)
        scene = self._entity_scene(player or {})
        killed = 0
        for zid, zombie in list(self.zombies.items()):
            if self._entity_scene(zombie) != scene:
                continue
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
            scene=scene,
        )

    def _try_drop_item(self, x, y, zombie=None):
        if len(self.items) >= self._max_items:
            return
        ztype = (zombie or {}).get("type")
        scene = self._entity_scene(zombie or {})
        if ztype in ("warden", "boss") and random.random() < 0.34:
            self.spawn_item(x, y, item_type=random.choice(("shield", "ammo_explosive", "parts")), scene=scene)
            return
        if ztype in ("screamer", "bloater", "spitter") and random.random() < 0.18:
            self.spawn_item(x, y, item_type="shield", scene=scene)
            return
        if ztype in ("brute", "armored", "leaper", "screamer", "bloater", "boss", "warden") and random.random() < 0.16:
            self.spawn_item(x, y, item_type="parts", scene=scene)
            return
        if ztype in ("runner", "crawler", "toxic") and random.random() < 0.14:
            self.spawn_item(x, y, item_type="ammo", scene=scene)
            return
        roll = random.random()
        if roll < 0.06:
            self.spawn_item(x, y, item_type="ammo", scene=scene)
        elif roll < 0.082:
            self.spawn_item(x, y, item_type="parts", scene=scene)
        elif roll < 0.11:
            self.spawn_item(x, y, scene=scene)

    def _try_drop_task_item(self, zombie, now=None):
        if len(self.items) >= self._max_items:
            return
        ztype = zombie.get("type")
        item_type = None
        lab_boost = (now is not None and now < self.lab_sample_until) or self._near_room_effect(
            zombie.get("x", 0), zombie.get("y", 0), "lab", padding=110
        )
        if ztype in ("toxic", "screamer", "bloater"):
            item_type = "sample" if random.random() < (0.55 if lab_boost else 0.40) else None
        elif ztype in ("runner", "brute", "armored", "boss"):
            item_type = "keycard" if random.random() < (0.55 if ztype != "runner" else 0.28) else None
        elif random.random() < 0.08 and not any(i.get("type") == "keycard" for i in self.items.values()):
            item_type = "keycard"
        elif random.random() < TASK_DROP_CHANCE * (0.92 if lab_boost else 0.42):
            item_type = "sample"
        if item_type:
            self.spawn_item(zombie["x"], zombie["y"], item_type=item_type, scene=self._entity_scene(zombie))

    def _item_pickup_reached(self, player, item):
        dx = player["x"] - item["x"]
        dy = player["y"] - item["y"]
        item_radius = item.get("radius", ITEM_R)
        visual_half_w = item_radius + 14
        visual_half_h = item_radius + 10
        if math.hypot(dx, dy) <= PLAYER_R + item_radius + 18:
            return True
        nearest_x = clamp(dx, -visual_half_w, visual_half_w)
        nearest_y = clamp(dy, -visual_half_h, visual_half_h)
        return (dx - nearest_x) ** 2 + (dy - nearest_y) ** 2 <= (PLAYER_R + 6) ** 2

    def _collect_items(self, now):
        for iid, item in list(self.items.items()):
            for sid, player in self.players.items():
                if player.get("dead") or player.get("paused"):
                    continue
                if self._entity_scene(player) != self._entity_scene(item):
                    continue
                if self._item_pickup_reached(player, item):
                    del self.items[iid]
                    self._apply_item(sid, item, now)
                    break

    def _feature_contains(self, feature, x, y, padding=0):
        if not feature:
            return False
        fx = feature.get("x", 0) - padding
        fy = feature.get("y", 0) - padding
        fw = feature.get("w", 0) + padding * 2
        fh = feature.get("h", 0) + padding * 2
        if feature.get("kind") == "pool":
            cx = feature.get("x", 0)
            cy = feature.get("y", 0)
            rx = max(1, feature.get("w", 40) * 0.55 + padding)
            ry = max(1, feature.get("h", 28) * 0.55 + padding)
            return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1
        return fx <= x <= fx + fw and fy <= y <= fy + fh

    def _room_at(self, x, y, padding=0):
        for feature in self.map_features:
            if feature.get("kind") == "room" and self._feature_contains(feature, x, y, padding=padding):
                return feature
        return None

    def _rooms_by_effect(self, effect):
        return [
            feature for feature in self.map_features
            if feature.get("kind") == "room" and feature.get("effect") == effect
        ]

    def _near_room_effect(self, x, y, effect, padding=0):
        return any(self._feature_contains(room, x, y, padding=padding) for room in self._rooms_by_effect(effect))

    def _room_return_point(self, room, player):
        fallback_x = (room or {}).get("x", self.spawn_point[0]) + (room or {}).get("w", 0) / 2
        fallback_y = (room or {}).get("y", self.spawn_point[1]) + (room or {}).get("h", 0) / 2
        target_x = finite_float(player.get("main_x"), fallback_x)
        target_y = finite_float(player.get("main_y"), fallback_y)
        target_x = clamp(target_x, PLAYER_R, MAP_W - PLAYER_R)
        target_y = clamp(target_y, PLAYER_R, MAP_H - PLAYER_R)
        if not self._overlaps_obstacle(target_x, target_y, PLAYER_R, SCENE_MAIN):
            return target_x, target_y

        candidates = [(target_x, target_y)]
        candidates.extend(sorted(
            self.floor_points or [self.spawn_point],
            key=lambda point: (point[0] - target_x) ** 2 + (point[1] - target_y) ** 2,
        )[:8])
        for cx, cy in candidates:
            rx, ry = self._resolve_obstacle_overlap(cx, cy, PLAYER_R, SCENE_MAIN)
            if not self._overlaps_obstacle(rx, ry, PLAYER_R, SCENE_MAIN):
                return rx, ry
        return self.safe_player_spawn()

    def _enter_room_scene(self, sid, player, room, now):
        if self._entity_scene(player) != SCENE_MAIN:
            return False
        if now < player.get("room_enter_cd", 0):
            return False
        scene_id = room.get("scene_id")
        scene = self.room_scenes.get(scene_id or "")
        if not scene:
            return False
        player["main_x"] = player["x"]
        player["main_y"] = player["y"]
        player["scene"] = scene_id
        player["scene_name"] = scene.get("name", room.get("label", "设施"))
        player["room_id"] = room.get("id", "")
        player["facility_room_id"] = ""
        player["facility_search"] = 0
        player["x"], player["y"] = scene.get("spawn", (240, ROOM_H / 2))
        player["vx"] = 0
        player["vy"] = 0
        player["keys"] = {}
        player["shooting"] = False
        player["room_enter_cd"] = now + 0.9
        player["room_hazard_grace_until"] = now + 10.0
        room["visited"] = True
        self._emit_scene_change(sid, reason="enter_room")
        self._emit_to("facility_pulse", {
            "pid": sid,
            "text": f"{room.get('label', '设施')}内部 · {self._room_hint(room.get('effect', ''))}",
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "col": "#aee6ff",
            "facility": room.get("effect", ""),
        }, [sid])
        self._trigger_room_entry_wave(sid, player, room, now)
        return True

    def _leave_room_scene(self, sid, player, now):
        scene_id = self._entity_scene(player)
        if scene_id == SCENE_MAIN:
            return False
        room = self._room_for_scene(scene_id)
        return_x, return_y = self._room_return_point(room, player)
        player["scene"] = SCENE_MAIN
        player["scene_name"] = "设施楼层"
        player["room_id"] = ""
        player["facility_room_id"] = ""
        player["facility_search"] = 0
        player["x"] = return_x
        player["y"] = return_y
        player["vx"] = 0
        player["vy"] = 0
        player["keys"] = {}
        player["shooting"] = False
        player["room_enter_cd"] = now + 1.1
        self._emit_scene_change(sid, reason="leave_room")
        self._emit_to("facility_pulse", {
            "pid": sid,
            "text": f"离开{(room or {}).get('label', '设施')}",
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "col": "#aee6ff",
            "facility": (room or {}).get("effect", ""),
        }, [sid])
        self._sweep_empty_room_scene(scene_id)
        return True

    def _room_exit_reached(self, player):
        scene_id = self._entity_scene(player)
        if scene_id == SCENE_MAIN:
            return False
        scene = self.room_scenes.get(scene_id)
        if not scene:
            return False
        exit_point = scene.get("exit", {})
        return math.hypot(player["x"] - exit_point.get("x", 0), player["y"] - exit_point.get("y", 0)) <= exit_point.get("radius", ROOM_DOOR_RADIUS) + PLAYER_R

    def _make_item_room_for_facility(self):
        while len(self.items) >= self._max_items:
            removable = next(
                (
                    iid for iid, item in self.items.items()
                    if item.get("type") not in OBJECTIVE_ITEM_TYPES
                ),
                None,
            )
            if removable is None:
                return
            self.items.pop(removable, None)

    def _spawn_item_in_feature(self, feature, item_type, emit=True, scene=SCENE_MAIN, force=True):
        if not feature:
            return None
        self._make_item_room_for_facility()
        margin = ITEM_R + 12
        if scene and scene != SCENE_MAIN:
            scene_def = self._scene_def(scene)
            loot = scene_def.get("loot", {"x": 240, "y": 160, "w": ROOM_W - 480, "h": ROOM_H - 320})
            for _ in range(24):
                x = random.uniform(loot["x"] + margin, loot["x"] + loot["w"] - margin)
                y = random.uniform(loot["y"] + margin, loot["y"] + loot["h"] - margin)
                if any(circ_rect(x, y, ITEM_R + 4, o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(x, y, ITEM_R + MAZE_WALL + 4, scene=scene)):
                    continue
                return self.spawn_item(x, y, item_type=item_type, emit=emit, scene=scene, force=force)
            return self.spawn_item(scene=scene, item_type=item_type, emit=emit, force=force)
        for _ in range(24):
            x = random.uniform(feature["x"] + margin, feature["x"] + feature["w"] - margin)
            y = random.uniform(feature["y"] + margin, feature["y"] + feature["h"] - margin)
            if any(circ_rect(x, y, ITEM_R + 4, o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(x, y, ITEM_R + MAZE_WALL + 4, scene=scene)):
                continue
            return self.spawn_item(x, y, item_type=item_type, emit=emit, scene=scene, force=force)
        x = feature["x"] + feature["w"] / 2
        y = feature["y"] + feature["h"] / 2
        return self.spawn_item(x, y, item_type=item_type, emit=emit, scene=scene, force=force)

    def _seed_facility_rewards(self):
        armories = self._rooms_by_effect("armory")
        if not armories:
            return
        if self.wave <= 1:
            reward = "weapon_rifle"
        elif self.wave == 2:
            reward = "weapon_shotgun"
        elif self.wave == 3:
            reward = "weapon_smg"
        else:
            reward = random.choice(("weapon_launcher", "vehicle", "parts"))
        armories[0]["pending_reward"] = reward

    def _exit_payload(self, exit_point):
        return {
            "id": exit_point["id"],
            "name": exit_point["name"],
            "text": exit_point["text"],
            "requires": exit_point["requires"],
            "requireText": self._requires_text(exit_point["requires"]),
            "rewardTitle": exit_point.get("rewardTitle", ""),
            "rewardText": exit_point.get("rewardText", ""),
            "shortReward": exit_point.get("shortReward", ""),
            "routeHook": exit_point.get("routeHook", ""),
            "ready": self._exit_ready(exit_point),
            "x": round(exit_point["x"], 1),
            "y": round(exit_point["y"], 1),
            "col": exit_point["color"],
        }

    def _reveal_one_exit(self, now, source="facility"):
        choices = [exit_point for exit_point in self.extractions if not exit_point.get("visible") and not exit_point.get("done")]
        if not choices:
            return None
        exit_point = random.choice(choices)
        exit_point["visible"] = True
        exit_point["ready_notified"] = self._exit_ready(exit_point)
        self.mission = exit_point
        payload = self._exit_payload(exit_point)
        payload["source"] = source
        self._emit("mission_revealed", payload)
        return exit_point

    def _facility_notice(self, player, now, text, color="#aee6ff", repeat_after=None, notice_key=None):
        key = f"{self._entity_scene(player)}:{player.get('facility_room_id', '')}:{notice_key or text}"
        if player.get("facility_notice_key") == key and now < player.get("facility_notice_repeat_at", 0):
            return
        if now < player.get("facility_notice_cd", 0):
            return
        player["facility_notice_key"] = key
        player["facility_notice_repeat_at"] = now + (repeat_after if repeat_after is not None else 9999)
        player["facility_notice_cd"] = now + 0.9
        self._emit_to("facility_pulse", {
            "pid": player["id"],
            "text": text,
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "col": color,
            "facility": player.get("facility_effect", ""),
            "noticeKey": notice_key or "",
        }, [player["id"]])

    def _scene_zombie_count(self, scene_id):
        return sum(1 for zombie in self.zombies.values() if self._entity_scene(zombie) == scene_id)

    def _room_hint(self, effect):
        return ROOM_ENTRY_HINTS.get(effect, "调查房间：搜索物资，同时承担房间风险。")

    def _room_reward_types(self, room, effect, player):
        if effect == "armory":
            if "pending_reward" in room:
                reward = room["pending_reward"]
            else:
                reward = self._armory_reward_type(player)
                room["pending_reward"] = reward
            rewards = [reward]
            ammo_reward = {
                "weapon_rifle": "ammo_rifle",
                "weapon_shotgun": "ammo_shell",
                "weapon_smg": "ammo_smg",
                "weapon_launcher": "ammo_explosive",
            }.get(reward)
            if ammo_reward:
                rewards.append(ammo_reward)
            elif reward not in ("ammo", "ammo_pistol", "ammo_rifle", "ammo_smg", "ammo_shell", "ammo_explosive"):
                rewards.append("ammo")
            rewards.append("parts")
            return rewards
        table = ROOM_REWARD_TABLE.get(effect)
        if not table:
            return []
        rewards = list(table.get("guaranteed", ()))
        bonus = list(table.get("bonus", ()))
        random.shuffle(bonus)
        rewards.extend(bonus[: max(0, int(table.get("bonus_count", 0)))])
        return rewards

    def _spawn_room_rewards(self, room, effect, player, scene_id):
        spawned = []
        primary_spawned = False
        for index, item_type in enumerate(self._room_reward_types(room, effect, player)):
            iid = self._spawn_item_in_feature(room, item_type, emit=True, scene=scene_id)
            if iid is not None:
                spawned.append(iid)
                if index == 0:
                    primary_spawned = True
        if effect == "armory" and primary_spawned:
            room.pop("pending_reward", None)
        return spawned

    def _room_reward_status(self, effect, fallback):
        table = ROOM_REWARD_TABLE.get(effect, {})
        return table.get("status", fallback)

    def _trigger_room_entry_wave(self, sid, player, room, now):
        scene_id = self._entity_scene(player)
        if scene_id == SCENE_MAIN:
            return 0
        scene = self.room_scenes.get(scene_id)
        if not scene or scene.get("entry_wave_spawned"):
            return 0
        scene["entry_wave_spawned"] = True
        room["alarm_spawned"] = True
        reason = room.get("effect", "director")
        queued = self._trigger_fog_wave(now, reason=reason, force=True, origin=player, scene=scene_id)
        if queued:
            self._facility_notice(
                player,
                now,
                f"{self._fog_scene(reason).get('name', '雾袭')}：房间内出现感染体",
                "#ff8a98",
                repeat_after=4.5,
                notice_key="room_entry_wave",
            )
        return queued

    def _apply_room_hazard(self, sid, player, scene_id, effect, dt, now):
        dps = ROOM_HAZARD_DPS.get(effect, 0)
        if dps <= 0 or scene_id == SCENE_MAIN:
            return 0
        if now < player.get("room_hazard_grace_until", 0):
            return 0
        before = player.get("hp", 0)
        self._damage_player(
            sid,
            dps * dt,
            now,
            source=f"room_hazard:{effect}",
            source_scene=scene_id,
        )
        return max(0, before - player.get("hp", before))

    def _trigger_lab_reactor(self, sid, player, room, now):
        if now < room.get("next_reactor_at", 0):
            return
        room["next_reactor_at"] = now + 8.5
        self.lab_sample_until = max(self.lab_sample_until, now + 9.0)
        scene_id = self._entity_scene(player)
        self._emit_to("lab_reactor", {
            "pid": sid,
            "text": "样本库共振：特殊感染体样本掉落提升 9 秒，感染信号正在靠近",
            "duration": 9.0,
            "spawned": 0,
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "col": "#b7ff47",
            "sceneId": scene_id,
        }, [sid])

    def _armory_reward_type(self, player):
        owned = set(self._unlocked_weapon_ids(player))
        for weapon_id in WEAPON_ORDER[1:]:
            if weapon_id not in owned:
                return f"weapon_{weapon_id}"
        if self.wave >= 2 and random.random() < 0.36:
            return "vehicle"
        return "parts" if random.random() < 0.48 else "ammo"

    def _apply_facility_effects(self, dt, now):
        for sid, player in list(self.players.items()):
            player["facility_label"] = ""
            player["facility_status"] = ""
            player["facility_effect"] = ""
            if player.get("dead") or player.get("paused"):
                player["facility_room_id"] = ""
                player["facility_search"] = 0
                continue
            scene_id = self._entity_scene(player)
            scene_features = self.map_features if scene_id == SCENE_MAIN else self._scene_def(scene_id).get("features", [])
            for feature in scene_features:
                if feature.get("kind") == "pool" and self._feature_contains(feature, player["x"], player["y"], padding=PLAYER_R):
                    self._damage_player(
                        sid,
                        FACILITY_TOXIC_DAMAGE_PER_SEC * dt,
                        now,
                        source="toxic_pool",
                        source_scene=scene_id,
                    )
                    player["facility_status"] = "污染区"
                    self._facility_notice(player, now, "地面污染正在灼伤你", "#b7ff47", repeat_after=4.0)
                    break
            if scene_id == SCENE_MAIN:
                room = self._room_at(player["x"], player["y"], padding=PLAYER_R * 0.65)
                if room:
                    if room.get("scene_id"):
                        label = room.get("label", "设施")
                        room_id = room.get("id", "")
                        effect = room.get("effect", "")
                        player["facility_label"] = label
                        player["facility_effect"] = effect
                        player["facility_status"] = f"按 F 进入{label}"
                        if player.get("facility_room_id") != room_id:
                            player["facility_room_id"] = room_id
                            player["facility_search"] = 0
                            self._facility_notice(
                                player,
                                now,
                                f"按 F 进入{label} · {self._room_hint(effect)}",
                                "#aee6ff",
                                notice_key="enter_prompt",
                            )
                        if player.pop("interact_requested", False):
                            self._enter_room_scene(sid, player, room, now)
                        continue
                player["interact_requested"] = False
            else:
                player["interact_requested"] = False
                if self._room_exit_reached(player):
                    self._leave_room_scene(sid, player, now)
                    continue
                room = self._room_for_scene(scene_id)
            if not room:
                player["facility_room_id"] = ""
                player["facility_search"] = 0
                continue
            effect = room.get("effect", "")
            label = room.get("label", "设施")
            room_id = room.get("id", "")
            player["facility_label"] = label
            player["facility_effect"] = effect
            entered_room = player.get("facility_room_id") != room_id
            if entered_room:
                player["facility_room_id"] = room_id
                player["facility_search"] = 0
                self._facility_notice(player, now, f"{label}：{self._room_hint(effect)}", "#aee6ff")

            hazard_suffix = ""
            if scene_id != SCENE_MAIN:
                if effect in ROOM_HAZARD_DPS:
                    grace_until = player.get("room_hazard_grace_until", 0)
                    _hazard_notice_cfg = {
                        "lab":      ("辐射污染正在灼伤你，尽快完成任务撤离", "#b7ff47"),
                        "archive":  ("空气污染正在侵蚀你，尽快完成任务撤离", "#ffcc44"),
                        "security": ("电弧放电正在击伤你，尽快完成任务撤离", "#d98cff"),
                        "morgue":   ("生化毒素正在侵蚀你，尽快完成任务撤离", "#ff8a98"),
                    }
                    if now < grace_until:
                        remaining = max(1, math.ceil(grace_until - now))
                        _msg, _col = _hazard_notice_cfg.get(effect, ("环境伤害即将开始", "#ffcc44"))
                        self._facility_notice(
                            player, now,
                            f"⚠ {remaining}秒后开始持续受到环境伤害",
                            "#ffcc44",
                            repeat_after=1.0,
                            notice_key="room_hazard_grace",
                        )
                        hazard_suffix = f" · {remaining}s后受到环境伤害"
                    else:
                        self._apply_room_hazard(sid, player, scene_id, effect, dt, now)
                        if player.get("dead"):
                            continue
                        _msg, _col = _hazard_notice_cfg.get(effect, ("环境伤害持续中", "#ff8a98"))
                        self._facility_notice(
                            player, now, _msg, _col,
                            repeat_after=3.5,
                            notice_key="room_hazard_dmg",
                        )
                        hazard_suffix = " · 持续受到环境伤害"

            if effect == "medbay":
                if room.get("searched"):
                    player["facility_search"] = 0
                    pending = any(self._entity_scene(item) == scene_id for item in self.items.values())
                    player["facility_status"] = ("医疗物资待拾取" if pending else "药柜已空") + hazard_suffix
                    continue
                player["facility_search"] = player.get("facility_search", 0) + dt
                progress = min(1, player["facility_search"] / (FACILITY_SEARCH_SECONDS * 0.78))
                player["facility_status"] = f"翻找药柜 {round(progress * 100)}%{hazard_suffix}"
                if entered_room:
                    self._facility_notice(player, now, "病房药柜可能有急救包，但翻找会弄出声音", "#48f0a0")
                if progress >= 1:
                    player["facility_search"] = 0
                    spawned = self._spawn_room_rewards(room, effect, player, scene_id)
                    if spawned:
                        room["searched"] = True
                        room["active"] = False
                        player["facility_status"] = self._room_reward_status(effect, "医疗物资已掉落") + hazard_suffix
                        self._emit_to("facility_used", {
                            "pid": sid,
                            "facility": "medbay",
                            "text": "病房翻出医疗物资",
                            "x": round(player["x"], 1),
                            "y": round(player["y"], 1),
                            "col": "#48f0a0",
                            "item": spawned[0],
                            "quiet": True,
                        }, [sid])
            elif effect == "generator":
                if room.get("searched"):
                    player["facility_search"] = 0
                    player["facility_status"] = "供电已恢复"
                elif self.task_counts.get("fuse", 0) > 0:
                    player["facility_search"] = player.get("facility_search", 0) + dt
                    progress = min(1, player["facility_search"] / (FACILITY_SEARCH_SECONDS * 0.86))
                    player["facility_status"] = f"接入电力 {round(progress * 100)}%"
                    if progress < 1:
                        continue
                    player["facility_search"] = 0
                    self.task_counts["fuse"] = max(0, self.task_counts.get("fuse", 0) - 1)
                    room["searched"] = True
                    room["active"] = False
                    self.power_on = True
                    self._spawn_room_rewards(room, effect, player, scene_id)
                    revealed = self._reveal_one_exit(now, source="generator")
                    player["facility_status"] = "供电已恢复"
                    self._emit("task_update", {
                        "pid": sid,
                        "type": "fuse",
                        "name": "保险丝",
                        "count": self.task_counts.get("fuse", 0),
                        "task": self._task_summary(),
                        "x": round(player["x"], 1),
                        "y": round(player["y"], 1),
                        "col": "#66d9ff",
                        "sceneId": scene_id,
                    })
                    self._emit_to("facility_used", {
                        "pid": sid,
                        "facility": "generator",
                        "text": f"机房恢复供电{('，' + revealed['name'] + ' 已定位') if revealed else ''}",
                        "x": round(player["x"], 1),
                        "y": round(player["y"], 1),
                        "col": "#66d9ff",
                    }, [sid])
                else:
                    player["facility_search"] = 0
                    player["facility_status"] = "需要保险丝"
                    self._facility_notice(player, now, "机房需要保险丝才能恢复供电", "#66d9ff")
            elif effect == "lab":
                if entered_room:
                    self._trigger_lab_reactor(sid, player, room, now)
                    self._facility_notice(player, now, "样本库共振中：击杀特殊感染体更容易掉样本", "#b7ff47")
                self.lab_sample_until = max(self.lab_sample_until, now + 6.0)
                left = max(0, self.lab_sample_until - now)
                if room.get("searched"):
                    player["facility_search"] = 0
                    pending = any(self._entity_scene(item) == scene_id for item in self.items.values())
                    player["facility_status"] = ("样本物资待拾取" if pending else "样本柜已空") + hazard_suffix
                    continue
                player["facility_search"] = player.get("facility_search", 0) + dt
                progress = min(1, player["facility_search"] / (FACILITY_SEARCH_SECONDS * 1.05))
                player["facility_status"] = f"采集样本 {round(progress * 100)}% · 样本共振 {left:.0f}s{hazard_suffix}"
                if progress >= 1:
                    player["facility_search"] = 0
                    spawned = self._spawn_room_rewards(room, effect, player, scene_id)
                    if spawned:
                        room["searched"] = True
                        player["facility_status"] = self._room_reward_status(effect, "样本容器已掉落") + hazard_suffix
                        self._emit_to("facility_used", {
                            "pid": sid,
                            "facility": "lab",
                            "text": "样本容器和研究物资已掉落",
                            "x": round(player["x"], 1),
                            "y": round(player["y"], 1),
                            "col": "#b7ff47",
                            "item": spawned[0],
                            "quiet": True,
                        }, [sid])
            elif effect == "archive":
                if room.get("searched"):
                    player["facility_search"] = 0
                    lore_pending = any(
                        item.get("type") == "lore" and self._entity_scene(item) == scene_id
                        for item in self.items.values()
                    )
                    player["facility_status"] = ("档案已掉落" if lore_pending else "档案已取走") + hazard_suffix
                    continue
                player["facility_search"] = player.get("facility_search", 0) + dt
                progress = min(1, player["facility_search"] / (FACILITY_SEARCH_SECONDS * 1.18))
                player["facility_status"] = f"检索档案 {round(progress * 100)}%{hazard_suffix}"
                if player["facility_search"] >= FACILITY_SEARCH_SECONDS * 1.18:
                    player["facility_search"] = 0
                    spawned = self._spawn_room_rewards(room, effect, player, scene_id)
                    if not spawned:
                        iid = self.spawn_item(player["x"], player["y"], item_type="lore", emit=True, scene=scene_id)
                        spawned = [iid] if iid is not None else []
                    if spawned:
                        room["lore_dropped"] = True
                        room["searched"] = True
                        room["active"] = False
                        player["facility_status"] = self._room_reward_status(effect, "档案已掉落") + hazard_suffix
                        if random.random() < 0.55:
                            self._reveal_one_exit(now, source="archive")
            elif effect == "security":
                if room.get("searched"):
                    player["facility_search"] = 0
                    player["facility_status"] = "安保柜已空" + hazard_suffix
                    continue
                if self.task_counts.get("keycard", 0) <= 0:
                    player["facility_search"] = 0
                    player["facility_status"] = "需要门禁卡" + hazard_suffix
                    self._facility_notice(player, now, "安保柜需要门禁卡，附近感染体可能携带", "#d98cff")
                    continue
                player["facility_search"] = player.get("facility_search", 0) + dt
                progress = min(1, player["facility_search"] / FACILITY_SEARCH_SECONDS)
                player["facility_status"] = f"破解安保柜 {round(progress * 100)}%{hazard_suffix}"
                if progress < 1:
                    continue
                player["facility_search"] = 0
                self.task_counts["keycard"] = max(0, self.task_counts.get("keycard", 0) - 1)
                room["searched"] = True
                room["active"] = False
                self._spawn_room_rewards(room, effect, player, scene_id)
                revealed = self._reveal_one_exit(now, source="security")
                player["facility_status"] = "安保柜已开" + hazard_suffix
                self._emit("task_update", {
                    "pid": sid,
                    "type": "keycard",
                    "name": "门禁卡",
                    "count": self.task_counts.get("keycard", 0),
                    "task": self._task_summary(),
                    "x": round(player["x"], 1),
                    "y": round(player["y"], 1),
                    "col": "#d98cff",
                    "sceneId": scene_id,
                })
                self._emit_to("facility_used", {
                    "pid": sid,
                    "facility": "security",
                    "text": f"安保柜打开{('，' + revealed['name'] + ' 已定位') if revealed else ''}",
                    "x": round(player["x"], 1),
                    "y": round(player["y"], 1),
                    "col": "#d98cff",
                }, [sid])
            elif effect == "morgue":
                self.lab_sample_until = max(self.lab_sample_until, now + 4.0)
                if room.get("searched"):
                    player["facility_search"] = 0
                    pending = any(self._entity_scene(item) == scene_id for item in self.items.values())
                    player["facility_status"] = ("停尸间物资待拾取" if pending else "尸袋已翻空") + hazard_suffix
                    continue
                if entered_room:
                    self._facility_notice(player, now, "停尸间会持续掉血，但能翻出样本和急救物资", "#b7ff47")
                player["facility_search"] = player.get("facility_search", 0) + dt
                progress = min(1, player["facility_search"] / (FACILITY_SEARCH_SECONDS * 0.92))
                player["facility_status"] = f"翻检尸袋 {round(progress * 100)}%{hazard_suffix}"
                if progress >= 1:
                    player["facility_search"] = 0
                    spawned = self._spawn_room_rewards(room, effect, player, scene_id)
                    if spawned:
                        room["searched"] = True
                        room["active"] = False
                        player["facility_status"] = self._room_reward_status(effect, "样本已掉落") + hazard_suffix
            elif effect == "armory":
                if room.get("searched"):
                    player["facility_search"] = 0
                    player["facility_status"] = "柜门已空" + hazard_suffix
                    continue
                player["facility_search"] = player.get("facility_search", 0) + dt
                progress = min(1, player["facility_search"] / FACILITY_SEARCH_SECONDS)
                player["facility_status"] = f"搜刮仓库 {round(progress * 100)}%{hazard_suffix}"
                if player["facility_search"] >= FACILITY_SEARCH_SECONDS:
                    player["facility_search"] = 0
                    spawned = self._spawn_room_rewards(room, effect, player, scene_id)
                    room["searched"] = True
                    room["active"] = False
                    primary_type = self.items.get(spawned[0], {}).get("type") if spawned else "parts"
                    meta = ITEM_TYPES.get(primary_type, {})
                    self._emit_to("facility_used", {
                        "pid": sid,
                        "facility": "armory",
                        "text": f"仓库找到 {meta.get('name', '补给')} 和弹药零件",
                        "x": round(player["x"], 1),
                        "y": round(player["y"], 1),
                        "col": meta.get("color", "#ffc247"),
                        "item": spawned[0] if spawned else None,
                        "quiet": True,
                    }, [sid])

    def _vehicle_ram(self, sid, player, now, zombie_grid):
        if now < player.get("vehicle_ram_cd", 0):
            return
        speed = math.hypot(player.get("vx", 0), player.get("vy", 0))
        if speed < self._player_speed(player) * 0.45:
            return
        hit = None
        scene = self._entity_scene(player)
        for zid, zombie in self._zombies_near(zombie_grid, player["x"], player["y"], PLAYER_R + 72):
            if zid not in self.zombies:
                continue
            if self._entity_scene(zombie) != scene:
                continue
            dist = math.hypot(zombie["x"] - player["x"], zombie["y"] - player["y"])
            if dist <= PLAYER_R + zombie.get("radius", 16) + 36:
                hit = (zid, zombie)
                break
        if not hit:
            return
        zid, zombie = hit
        player["vehicle_ram_cd"] = now + VEHICLE_RAM_COOLDOWN
        damage = VEHICLE_RAM_DAMAGE + min(34, player.get("level", 1) * 3)
        zombie["hp"] -= damage
        zombie["last_hit_by"] = sid
        dx = zombie["x"] - player["x"]
        dy = zombie["y"] - player["y"]
        dist = math.hypot(dx, dy) or 1
        zombie["x"], zombie["y"] = self.move_col(
            zombie["x"], zombie["y"], zombie.get("radius", 16),
            dx / dist * 70, dy / dist * 70,
            scene=scene,
        )
        self._emit_near("vehicle_hit", {
            "pid": sid,
            "zid": zid,
            "x": round(zombie["x"], 1),
            "y": round(zombie["y"], 1),
            "damage": round(damage, 1),
            "col": "#ffc247",
        }, zombie["x"], zombie["y"], include=sid, scene=scene)
        if zombie["hp"] <= 0:
            self._kill_zombie(sid, zid, zombie, now, reason="vehicle")

    def _expire_player_effects(self, now):
        for player in self.players.values():
            for field, typ in (("rapid_until", "rapid"), ("spread_until", "spread"), ("shield_until", "shield")):
                if player.get(field) and now > player.get(field, 0):
                    player[field] = 0
                    self._emit("item_end", {"pid": player["id"], "type": typ})
            if player.get("vehicle_until", 0) and now > player.get("vehicle_until", 0):
                player["vehicle_until"] = 0
                player["vehicle_ram_cd"] = 0
                if not player.get("vehicle_end_notified"):
                    self._emit_to("vehicle_end", {"pid": player["id"]}, [player["id"]])
                player["vehicle_end_notified"] = True

    def _try_reload(self, sid, player, now, manual=False):
        if player.get("dead") or player.get("reload_until", 0) > now:
            return False
        wid, meta, state = self._sync_weapon_fields(player)
        ammo_type = meta.get("ammo_type", "pistol")
        mag_size = player.get("mag_size", meta["mag_size"])
        reserve = self._ammo_reserve(player, ammo_type)
        if player.get("ammo", 0) >= mag_size or reserve <= 0:
            return False
        player["shooting"] = False
        duration = meta.get("reload_seconds", RELOAD_SECONDS)
        player["reload_until"] = now + duration
        payload = {
            "pid": sid,
            "duration": duration,
            "ammo": player.get("ammo", 0),
            "weapon": wid,
            "weaponName": meta["name"],
            "magSize": mag_size,
        }
        payload.update(self._current_ammo_payload(player, ammo_type))
        self._emit_to("reload_start", payload, [sid])
        return True

    def _finish_reload(self, player, now):
        if not player.get("reload_until") or player.get("reload_until", 0) > now:
            return
        player["reload_until"] = 0
        wid, meta, state = self._sync_weapon_fields(player)
        ammo_type = meta.get("ammo_type", "pistol")
        mag_size = player.get("mag_size", meta["mag_size"])
        needed = max(0, mag_size - player.get("ammo", 0))
        reserve = self._ammo_reserve(player, ammo_type)
        loaded = min(needed, reserve)
        player["ammo"] = player.get("ammo", 0) + loaded
        self._set_ammo_reserve(player, ammo_type, reserve - loaded)
        state["ammo"] = player["ammo"]
        payload = {
            "pid": player["id"],
            "ammo": player.get("ammo", 0),
            "weapon": wid,
            "weaponName": meta["name"],
            "magSize": mag_size,
        }
        payload.update(self._current_ammo_payload(player, ammo_type))
        self._emit_to("reload_done", payload, [player["id"]])

    def _segment_blocked(self, x1, y1, x2, y2, radius=3, scene=SCENE_MAIN):
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist <= 0.01:
            return False
        search_r = dist / 2 + MAZE_WALL + radius
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        for obstacle in self._near_obstacles(mx, my, search_r, scene=scene):
            if self._segment_hits_expanded_rect(x1, y1, x2, y2, obstacle, radius):
                return True
        return False

    @staticmethod
    def _segment_hits_expanded_rect(x1, y1, x2, y2, obstacle, radius):
        left = obstacle["x"] - radius
        right = obstacle["x"] + obstacle["w"] + radius
        top = obstacle["y"] - radius
        bottom = obstacle["y"] + obstacle["h"] + radius
        if left <= x1 <= right and top <= y1 <= bottom:
            return True
        if left <= x2 <= right and top <= y2 <= bottom:
            return True
        dx = x2 - x1
        dy = y2 - y1
        t0 = 0.0
        t1 = 1.0
        for p, q in (
            (-dx, x1 - left),
            (dx, right - x1),
            (-dy, y1 - top),
            (dy, bottom - y1),
        ):
            if abs(p) < 0.000001:
                if q < 0:
                    return False
                continue
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                t0 = max(t0, r)
            else:
                if r < t0:
                    return False
                t1 = min(t1, r)
        return True

    def _nearest_melee_target(self, player, zombie_grid=None, reach=MELEE_RANGE, require_arc=False):
        zombie_grid = zombie_grid or self._build_grid(self.zombies)
        px = player["x"]
        py = player["y"]
        scene = self._entity_scene(player)
        aim = player.get("aim_angle", 0)
        best = None
        query_r = PLAYER_R + reach + 42
        for zid, zombie in self._zombies_near(zombie_grid, px, py, query_r):
            if zid not in self.zombies:
                continue
            if self._entity_scene(zombie) != scene:
                continue
            dx = zombie["x"] - px
            dy = zombie["y"] - py
            dist = math.hypot(dx, dy)
            allowed = PLAYER_R + zombie.get("radius", 16) + reach
            if dist > allowed:
                continue
            if require_arc and dist > PLAYER_R + zombie.get("radius", 16) + 14:
                delta = ((math.atan2(dy, dx) - aim + math.pi) % (math.pi * 2)) - math.pi
                if abs(delta) > MELEE_ARC / 2:
                    continue
            if self._segment_blocked(px, py, zombie["x"], zombie["y"], scene=scene):
                continue
            score = dist
            if best is None or score < best[0]:
                best = (score, zid, zombie)
        return None if best is None else (best[1], best[2])

    def _try_melee(self, sid, player, now, zombie_grid=None, reach=MELEE_RANGE, require_arc=False):
        if player.get("dead") or now < player.get("melee_cd", 0):
            return False
        target = self._nearest_melee_target(player, zombie_grid, reach=reach, require_arc=require_arc)
        if not target:
            return False
        zid, zombie = target
        dx = zombie["x"] - player["x"]
        dy = zombie["y"] - player["y"]
        dist = math.hypot(dx, dy) or 1.0
        ux = dx / dist
        uy = dy / dist
        damage = round((
            MELEE_DAMAGE
            + max(0, player.get("level", 1) - 1)
            + max(0, player.get("weapon_level", 1) - 1) * 2
        ) * (1.5 if now < player.get("damage_boost_until", 0) else 1.0), 1)
        player["melee_cd"] = now + MELEE_COOLDOWN
        player["last_melee_at"] = now
        zombie["hp"] -= damage
        zombie["last_hit_by"] = sid
        zombie["x"], zombie["y"] = self.move_col(
            zombie["x"], zombie["y"], zombie.get("radius", 16),
            ux * MELEE_KNOCKBACK, uy * MELEE_KNOCKBACK,
            scene=self._entity_scene(zombie),
        )
        self._emit_near("melee_swing", {
            "pid": sid,
            "zid": zid,
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "tx": round(zombie["x"], 1),
            "ty": round(zombie["y"], 1),
            "angle": round(math.atan2(uy, ux), 3),
            "hit": True,
            "damage": round(damage, 1),
            "col": player["color"],
        }, player["x"], player["y"], include=sid, scene=self._entity_scene(player))
        if zombie["hp"] <= 0:
            self._kill_zombie(sid, zid, zombie, now, reason="melee")
        return True

    def _try_shoot(self, sid, player, now, force=False, zombie_grid=None):
        if player.get("dead") or (not player.get("shooting") and not force):
            return
        if now - player.get("last_melee_at", -999) < SERVER_DT * 0.75:
            return
        if self._try_melee(sid, player, now, zombie_grid=zombie_grid, reach=MELEE_AUTO_RANGE, require_arc=False):
            return
        if player.get("reload_until", 0) > now:
            return
        wid, meta, state = self._sync_weapon_fields(player)
        ammo_type = meta.get("ammo_type", "pistol")
        interval = meta.get("fire_interval", FIRE_INTERVAL) * (RAPID_FIRE_MULT if now < player.get("rapid_until", 0) else 1)
        if now < player.get("fire_cd", 0):
            return
        ammo_cost = max(1, int(meta.get("ammo_cost", 1)))
        if player.get("ammo", 0) < ammo_cost:
            self._try_reload(sid, player, now)
            return
        player["fire_cd"] = now + interval
        player["ammo"] = max(0, player.get("ammo", 0) - ammo_cost)
        state["ammo"] = player["ammo"]
        payload = {
            "pid": sid,
            "ammo": player.get("ammo", 0),
            "weapon": wid,
            "weaponName": meta["name"],
            "magSize": player.get("mag_size", meta["mag_size"]),
            "pellets": meta.get("pellets", 1),
        }
        payload.update(self._current_ammo_payload(player, ammo_type))
        self._emit_to("shot_fired", payload, [sid])
        base_angle = player.get("aim_angle", 0)
        pellets = max(1, int(meta.get("pellets", 1)))
        spread = float(meta.get("spread", 0.0))
        if pellets == 1:
            angles = [base_angle + (random.uniform(-spread, spread) if spread else 0)]
        else:
            angles = [
                base_angle + (-spread / 2 + spread * i / max(1, pellets - 1)) + random.uniform(-0.018, 0.018)
                for i in range(pellets)
            ]
        if now < player.get("spread_until", 0):
            angles = [angle - SPREAD_ANGLE for angle in angles] + angles + [angle + SPREAD_ANGLE for angle in angles]
        muzzle = meta.get("muzzle", MUZZLE_FORWARD)
        muzzle_x = player["x"] + math.cos(base_angle) * muzzle
        muzzle_y = player["y"] + math.sin(base_angle) * muzzle
        for angle in angles:
            if len(self.bullets) >= MAX_BULLETS:
                break
            bid = self._next_b
            self._next_b += 1
            speed = meta.get("bullet_speed", BULLET_SPEED)
            self.bullets[bid] = {
                "id": bid,
                "owner": sid,
                "weapon": wid,
                "scene": self._entity_scene(player),
                "x": muzzle_x,
                "y": muzzle_y,
                "spawn_x": muzzle_x,
                "spawn_y": muzzle_y,
                "prev_x": muzzle_x,
                "prev_y": muzzle_y,
                "born_tick": self.tick_id,
                "shot_seq": player.get("input_seq", player.get("ack_seq", 0)),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "radius": meta.get("bullet_radius", BULLET_R),
                "life": meta.get("bullet_life", BULLET_LIFE),
                "damage": round((
                    meta.get("damage", BULLET_DAMAGE)
                    + max(0, player.get("level", 1) - 1) * 2
                    + max(0, player.get("weapon_level", 1) - 1) * 3
                    + min(18, (player.get("combo", 0) // 5) * 2)
                ) * (1.5 if now < player.get("damage_boost_until", 0) else 1.0), 1),
                "explosion_radius": meta.get("explosion_radius", 0),
                "explosion_damage": meta.get("explosion_damage", meta.get("damage", BULLET_DAMAGE)),
                "boss_damage_mult": meta.get("boss_damage_mult", 1.0),
                "pierce": meta.get("pierce", 0),
                "hit_ids": set(),
                "color": meta.get("color") or player["color"],
            }

    def _update_bullets(self, dt, now):
        zombie_grid = self._build_grid(self.zombies)
        for bid, bullet in list(self.bullets.items()):
            scene = self._entity_scene(bullet)
            newborn = bullet.get("born_tick") == self.tick_id
            if not newborn:
                bullet["life"] -= dt
                bullet["prev_x"] = bullet["x"]
                bullet["prev_y"] = bullet["y"]
                bullet["x"] += bullet["vx"] * dt
                bullet["y"] += bullet["vy"] * dt
            scene_def = self._scene_def(scene)
            mw = scene_def.get("mw", MAP_W)
            mh = scene_def.get("mh", MAP_H)
            if bullet["life"] <= 0 or bullet["x"] < -40 or bullet["x"] > mw + 40 or bullet["y"] < -40 or bullet["y"] > mh + 40:
                if bullet.get("explosion_radius", 0) > 0 and bullet["life"] <= 0:
                    self._explode_projectile(bullet, now)
                self.bullets.pop(bid, None)
                continue
            if any(pt_in_rect(bullet["x"], bullet["y"], o["x"], o["y"], o["w"], o["h"]) for o in self._near_obstacles(bullet["x"], bullet["y"], bullet["radius"] + MAZE_WALL, scene=scene)):
                if bullet.get("explosion_radius", 0) > 0:
                    self._explode_projectile(bullet, now)
                self.bullets.pop(bid, None)
                continue

            hit_id = None
            hit_zombie = None
            for zid, zombie in self._zombies_near(zombie_grid, bullet["x"], bullet["y"], bullet["radius"] + 34):
                if zid not in self.zombies:
                    continue
                if self._entity_scene(zombie) != scene:
                    continue
                if zid in bullet.get("hit_ids", set()):
                    continue
                if math.hypot(bullet["x"] - zombie["x"], bullet["y"] - zombie["y"]) <= bullet["radius"] + zombie["radius"]:
                    hit_id = zid
                    hit_zombie = zombie
                    break
            if hit_id is None:
                continue

            damage = bullet["damage"]
            if hit_zombie.get("type") == "boss":
                damage *= bullet.get("boss_damage_mult", 1.0)
            hit_zombie["hp"] -= damage
            hit_zombie["last_hit_by"] = bullet["owner"]
            bullet.setdefault("hit_ids", set()).add(hit_id)
            if bullet.get("explosion_radius", 0) > 0:
                self._explode_projectile(bullet, now)
                self.bullets.pop(bid, None)
            elif bullet.get("pierce", 0) > 0:
                bullet["pierce"] -= 1
            else:
                self.bullets.pop(bid, None)
            if hit_zombie["hp"] <= 0:
                self._kill_zombie(bullet["owner"], hit_id, hit_zombie, now, reason="bullet")

    def _explode_projectile(self, bullet, now):
        radius = bullet.get("explosion_radius", 0)
        if radius <= 0:
            return
        owner = bullet.get("owner")
        scene = self._entity_scene(bullet)
        damage = bullet.get("explosion_damage", bullet.get("damage", BULLET_DAMAGE))
        x = bullet["x"]
        y = bullet["y"]
        self._emit_near("grenade_explode", {
            "pid": owner,
            "x": round(x, 1),
            "y": round(y, 1),
            "r": radius,
            "col": bullet.get("color", "#ff8844"),
        }, x, y, radius=radius + EVENT_INTEREST_RADIUS * 0.35, include=owner, scene=scene)
        for zid, zombie in list(self.zombies.items()):
            if self._entity_scene(zombie) != scene:
                continue
            dist = math.hypot(zombie["x"] - x, zombie["y"] - y)
            if dist > radius + zombie.get("radius", 16):
                continue
            scale = 1 - min(0.72, dist / max(1, radius) * 0.62)
            boss_mult = bullet.get("boss_damage_mult", 1.0) if zombie.get("type") == "boss" else 1.0
            zombie["hp"] -= damage * scale * boss_mult
            zombie["last_hit_by"] = owner
            if zombie["hp"] <= 0:
                self._kill_zombie(owner, zid, zombie, now, reason="blast")

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
        }, zombie["x"], zombie["y"], include=sid, scene=self._entity_scene(zombie))
        killer = self.players.get(sid)
        if killer and killer.get("kills") == 1:
            self._emit_to("first_blood", {
                "pid": sid,
                "x": round(zombie["x"], 1),
                "y": round(zombie["y"], 1),
                "sceneId": self._entity_scene(zombie),
            }, [sid])
        if zombie["type"] == "bloater":
            self._explode_bloater(sid, zid, zombie, now)
        self._try_drop_task_item(zombie, now)
        self._try_drop_item(zombie["x"], zombie["y"], zombie)

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
        }, x, y, radius=BLOATER_RADIUS + EVENT_INTEREST_RADIUS * 0.5, include=sid, scene=self._entity_scene(zombie))

        for psid, player in list(self.players.items()):
            if self._entity_scene(player) != self._entity_scene(zombie):
                continue
            if math.hypot(player["x"] - x, player["y"] - y) <= BLOATER_RADIUS + PLAYER_R:
                self._damage_player(
                    psid,
                    BLOATER_PLAYER_DAMAGE,
                    now,
                    source=f"bloater:{zid}",
                    source_scene=self._entity_scene(zombie),
                )

        for other_id, other in list(self.zombies.items()):
            if other_id not in self.zombies:
                continue
            if self._entity_scene(other) != self._entity_scene(zombie):
                continue
            if math.hypot(other["x"] - x, other["y"] - y) > BLOATER_RADIUS + other.get("radius", 16):
                continue
            other["hp"] -= BLOATER_ZOMBIE_DAMAGE
            other["last_hit_by"] = sid
            if other["hp"] <= 0:
                self._kill_zombie(sid, other_id, other, now, reason="blast")

    def _damage_player(self, sid, amount, now, source=None, source_scene=None):
        player = self.players.get(sid)
        if not player or player.get("dead") or self._player_protected(player, now):
            return
        if source_scene is not None and self._entity_scene(player) != source_scene:
            return
        player["hp"] -= amount
        if player["hp"] <= 0:
            self._kill_player(sid, source or "zombie", now)

    def _kill_player(self, sid, killer, now):
        player = self.players.get(sid)
        if not player or player.get("dead"):
            return
        player["paused"] = False
        player["dead"] = True
        player["death_time"] = now
        player["hp"] = 0
        player["vx"] = 0
        player["vy"] = 0
        player["shooting"] = False
        player["reload_until"] = 0
        player["vehicle_until"] = 0
        player["vehicle_ram_cd"] = 0
        player["lives"] = max(0, int(player.get("lives", PLAYER_STAGE_LIVES)) - 1)
        self._emit_near("p_die", {
            "pid": sid,
            "killer": killer,
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "col": player["color"],
            "lives": player.get("lives", 0),
            "maxLives": player.get("max_lives", PLAYER_STAGE_LIVES),
        }, player["x"], player["y"], include=sid, scene=self._entity_scene(player))

    def _try_dash(self, sid, player, now):
        if player.get("dead") or player.get("paused") or now < player.get("dash_cd", 0):
            return
        dx, dy = self._input_dir(player.get("keys", {}))
        if not dx and not dy:
            dx = math.cos(player.get("aim_angle", 0))
            dy = math.sin(player.get("aim_angle", 0))
        sx, sy = player["x"], player["y"]
        dash_steps = 4
        step_dist = DASH_DIST / dash_steps
        cx, cy = player["x"], player["y"]
        scene = self._entity_scene(player)
        for _ in range(dash_steps):
            cx, cy = self.move_col(cx, cy, PLAYER_R, dx * step_dist, dy * step_dist, scene=scene)
        player["x"], player["y"] = cx, cy
        player["vx"] = dx * self._player_speed(player) * 0.22
        player["vy"] = dy * self._player_speed(player) * 0.22
        player["dash_cd"] = now + DASH_CD
        self._emit_near("p_dash", {
            "pid": sid,
            "sx": round(sx, 1),
            "sy": round(sy, 1),
            "x": round(player["x"], 1),
            "y": round(player["y"], 1),
            "cd": DASH_CD,
            "col": player["color"],
        }, player["x"], player["y"], include=sid, scene=scene)

    def _update_players(self, dt, now):
        zombie_grid = None
        for sid, player in list(self.players.items()):
            if player.get("combo") and now > player.get("combo_until", 0):
                player["combo"] = 0
            if player.get("dead"):
                player["vx"] = 0
                player["vy"] = 0
                player["fire_requested"] = False
                player["ack_seq"] = max(player.get("ack_seq", 0), player.get("input_seq", 0))
                continue
            if player.get("paused"):
                player["keys"] = {}
                player["shooting"] = False
                player["fire_requested"] = False
                player["vx"] = 0
                player["vy"] = 0
                player["ack_seq"] = max(player.get("ack_seq", 0), player.get("input_seq", 0))
                continue
            self._finish_reload(player, now)

            dx, dy = self._input_dir(player.get("keys", {}))
            speed = self._player_speed(player, now)
            vehicle_active = now < player.get("vehicle_until", 0)
            if vehicle_active:
                speed *= VEHICLE_SPEED_MULT
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
                player["x"], player["y"] = self.move_col(player["x"], player["y"], PLAYER_R, player["vx"] * dt, player["vy"] * dt, scene=self._entity_scene(player))
                if vehicle_active:
                    if zombie_grid is None:
                        zombie_grid = self._build_grid(self.zombies)
                    self._vehicle_ram(sid, player, now, zombie_grid)
            force_fire = bool(player.pop("fire_requested", False))
            if player.get("shooting") or force_fire:
                self._refresh_player_aim(player)
                if zombie_grid is None:
                    zombie_grid = self._build_grid(self.zombies)
                self._try_shoot(sid, player, now, force=force_fire, zombie_grid=zombie_grid)
            player["ack_seq"] = max(player.get("ack_seq", 0), player.get("input_seq", 0))

    def _zombie_target(self, zombie, alive, now):
        candidates = []
        scene = self._entity_scene(zombie)
        for player in alive:
            if self._entity_scene(player) != scene:
                continue
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

    def _steer_zombie(self, zombie, target, speed, dt, now=0.0):
        dx = target["x"] - zombie["x"]
        dy = target["y"] - zombie["y"]
        dist = math.hypot(dx, dy)
        if dist <= 0.01 or speed <= 0:
            return 0, 0, zombie["x"], zombie["y"], dist
        base_angle = math.atan2(dy, dx)
        step = speed * dt
        direct_vx = math.cos(base_angle) * speed
        direct_vy = math.sin(base_angle) * speed
        scene = self._entity_scene(zombie)
        direct_x, direct_y = self.move_col(zombie["x"], zombie["y"], zombie["radius"], direct_vx * dt, direct_vy * dt, scene=scene)
        direct_moved = math.hypot(direct_x - zombie["x"], direct_y - zombie["y"])
        direct_d2 = (target["x"] - direct_x) ** 2 + (target["y"] - direct_y) ** 2
        blocked = direct_moved < step * 0.72 or direct_d2 >= dist * dist - step * 0.45
        if not blocked:
            zombie["avoid_side"] = 0
            zombie["stuck_for"] = 0
            if dist > 80:
                wander_phase = (hash(zombie.get("id", 0)) & 0x3FF) * (math.pi * 2 / 1024)
                wander = 0.18 * math.sin(now * 0.85 + wander_phase)
                wvx = math.cos(base_angle + wander) * speed
                wvy = math.sin(base_angle + wander) * speed
                wx, wy = self.move_col(zombie["x"], zombie["y"], zombie["radius"], wvx * dt, wvy * dt, scene=scene)
                if math.hypot(wx - zombie["x"], wy - zombie["y"]) >= step * 0.68:
                    return wvx, wvy, wx, wy, dist
            return direct_vx, direct_vy, direct_x, direct_y, dist

        side = zombie.get("avoid_side") or (1 if zombie.get("id", 0) % 2 else -1)
        zombie["avoid_side"] = side
        offsets = (side * 1.35, side * 1.57, side * 1.08, side * 0.74, side * 2.05, -side * 1.57, -side * 1.08, 0)
        best = None
        for rank, offset in enumerate(offsets):
            angle = base_angle + offset
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            nx, ny = self.move_col(zombie["x"], zombie["y"], zombie["radius"], vx * dt, vy * dt, scene=scene)
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
            nx, ny = self.move_col(zombie["x"], zombie["y"], zombie["radius"], vx * dt, vy * dt, scene=scene)
            if math.hypot(nx - zombie["x"], ny - zombie["y"]) < step * 0.25:
                zombie["stuck_for"] = zombie.get("stuck_for", 0) + dt
                zombie["path_time"] = 0
            return vx, vy, nx, ny, dist
        _, vx, vy, nx, ny, moved = best
        zombie["stuck_for"] = 0 if moved >= step * 0.48 else zombie.get("stuck_for", 0) + dt
        stuck_for = zombie.get("stuck_for", 0)
        if stuck_for > PATHFIND_STUCK_REPATH_SECONDS:
            zombie["path_time"] = 0
        if stuck_for > ZOMBIE_STUCK_AFTER:
            zombie["avoid_side"] = -zombie.get("avoid_side", 1) or -1
            zombie["path_time"] = 0
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
            if self._entity_scene(other) != self._entity_scene(zombie):
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
        }, zombie["x"], zombie["y"], scene=self._entity_scene(zombie))

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
        }, zombie["x"], zombie["y"], scene=self._entity_scene(zombie))
        return speed * LEAPER_SPEED_MULT

    def _maybe_boss_phase(self, zid, zombie, now):
        if zombie["type"] != "boss":
            return
        hp_ratio = zombie.get("hp", 0) / max(1, zombie.get("max_hp", 1))
        phase = 0
        if hp_ratio <= 0.4:
            phase = 2
        elif hp_ratio <= 0.7:
            phase = 1
        if phase <= zombie.get("phase", 0):
            return
        zombie["phase"] = phase
        zombie["rally_until"] = max(zombie.get("rally_until", 0), now + 5.0)
        summon_plan = ("stalker", "spitter", "runner") if phase == 1 else ("warden", "stalker", "screamer", "bloater")
        spawned = 0
        scene = self._entity_scene(zombie)
        for index in range(4 + phase * 3 + min(4, self.wave // 2)):
            if len(self.zombies) >= MAX_ZOMBIES:
                break
            ztype = summon_plan[index % len(summon_plan)]
            if self.wave < ZOMBIE_TYPES[ztype].get("unlock", 1):
                ztype = "runner"
            x, y = self.safe_fog_spawn(origin=zombie, scene=scene)
            new_id = self.spawn_zombie(x=x, y=y, ztype=ztype, emit=False, pressure=True, scene=scene)
            if not new_id:
                continue
            spawned += 1
            self.zombies[new_id]["rally_until"] = max(self.zombies[new_id].get("rally_until", 0), now + 2.8)
        self._emit_near("boss_phase", {
            "zid": zid,
            "phase": phase,
            "spawned": spawned,
            "x": round(zombie["x"], 1),
            "y": round(zombie["y"], 1),
            "hp": round(max(0, zombie.get("hp", 0)), 1),
            "maxHp": zombie.get("max_hp", 1),
            "col": zombie.get("color", "#d9445f"),
            "text": "黑墙巨像撕开墙体，新的感染体从雾里挤出。",
        }, zombie["x"], zombie["y"], radius=EVENT_INTEREST_RADIUS * 1.4, scene=scene)

    def _maybe_boss_slam(self, zid, zombie, target, dist, now):
        if zombie["type"] != "boss":
            return
        if now < zombie.get("slam_cd", 0):
            return
        phase = zombie.get("phase", 0)
        radius = 190 + phase * 44
        if dist > radius + 70:
            zombie["slam_cd"] = now + max(2.4, 4.2 - phase * 0.55)
            return
        zombie["slam_cd"] = now + max(2.2, 4.0 - phase * 0.6)
        hit = 0
        scene = self._entity_scene(zombie)
        for sid, player in self.players.items():
            if player.get("dead") or player.get("paused"):
                continue
            if self._entity_scene(player) != scene:
                continue
            pd = math.hypot(player["x"] - zombie["x"], player["y"] - zombie["y"])
            if pd <= radius + PLAYER_R:
                hit += 1
                self._damage_player(
                    sid,
                    18 + phase * 8 + min(8, self.wave),
                    now,
                    source=f"boss_slam:{zid}",
                    source_scene=scene,
                )
                dx = player["x"] - zombie["x"]
                dy = player["y"] - zombie["y"]
                mag = math.hypot(dx, dy) or 1
                player["x"], player["y"] = self.move_col(player["x"], player["y"], PLAYER_R, dx / mag * 48, dy / mag * 48, scene=scene)
        self._emit_near("boss_slam", {
            "zid": zid,
            "phase": phase,
            "hit": hit,
            "x": round(zombie["x"], 1),
            "y": round(zombie["y"], 1),
            "r": radius,
            "col": zombie.get("color", "#d9445f"),
        }, zombie["x"], zombie["y"], scene=scene)

    def _apply_route_reward(self, now, exit_point):
        reward = self._route_reward_payload(exit_point)
        route = reward.get("route")
        affected = 0
        if route == "service":
            amounts = self._service_ammo_reward_amounts()
            for player in self.players.values():
                for ammo_type, amount in amounts.items():
                    self._add_ammo_reserve(player, ammo_type, amount)
                self._sync_weapon_fields(player)
                affected += 1
            reward["amount"] = sum(amounts.values())
            reward["ammo"] = dict(amounts)
            reward["rewardText"] = self._ammo_reward_text(amounts)
        elif route == "lab":
            self.next_stage_reveal = True
            for sid, player in self.players.items():
                player["lore"] = player.get("lore", 0) + 1
                file_text = CASE_FILES[(player["lore"] - 1) % len(CASE_FILES)]
                self._emit_to("lore_found", {
                    "pid": sid,
                    "count": player["lore"],
                    "text": file_text,
                    "col": player["color"],
                }, [sid])
                affected += 1
        elif route == "security":
            amount = 3 + min(3, self.wave // 3)
            for player in self.players.values():
                player["materials"] = player.get("materials", 0) + amount
                owned = set(self._unlocked_weapon_ids(player))
                for weapon_id in WEAPON_ORDER[1:]:
                    if weapon_id not in owned:
                        self._unlock_weapon(player, weapon_id, now)
                        break
                affected += 1
            reward["amount"] = amount
        elif route == "archive":
            for sid, player in self.players.items():
                self._add_ammo_reserve(player, "explosive", 1)
                player["shield_until"] = max(player.get("shield_until", 0), now + 6.0)
                player["lore"] = player.get("lore", 0) + 1
                file_text = CASE_FILES[(player["lore"] - 1) % len(CASE_FILES)]
                self._emit_to("lore_found", {
                    "pid": sid,
                    "count": player["lore"],
                    "text": file_text,
                    "col": player["color"],
                }, [sid])
                affected += 1
            reward["amount"] = 1
            # Archive-route evacuation is a deliberate per-extraction scare, separate from room entry alarms.
            self._trigger_fog_wave(now, reason="archive", force=True)
        reward["affected"] = affected
        return reward

    def _begin_intermission(self, now, exit_point, players_in_zone, route_reward):
        self.bullets.clear()
        self.pending_fog_spawns.clear()
        self.fog_active_until = 0.0
        ending = self._is_final_wave(self.wave)
        for player in self.players.values():
            player["keys"] = {}
            player["shooting"] = False
            player["vx"] = 0
            player["vy"] = 0
            player["paused"] = False
            player["protect_until"] = max(player.get("protect_until", 0), now + 999)
        self.intermission = {
            "clearedWave": self.wave,
            "nextWave": self.wave + 1,
            "name": exit_point.get("name", "撤离终端"),
            "route": route_reward.get("route"),
            "rewardTitle": route_reward.get("rewardTitle"),
            "rewardText": route_reward.get("rewardText"),
            "shortReward": route_reward.get("shortReward"),
            "routeHook": route_reward.get("routeHook"),
            "ending": ending,
            "endingTitle": "主线结局：B13 层不存在",
            "endingText": "撤离终端打印出所有幸存者的死亡时间，最后一行是下一分钟。你们不是第一次来到这里，感染源一直在用撤离路线筛选能走到更深处的人。",
            "affected": route_reward.get("affected", 0),
            "amount": route_reward.get("amount", 0),
            "exit": dict(exit_point),
            "players": list(players_in_zone),
            "routeReward": dict(route_reward),
            "ready": [],
            "startedAt": now,
        }
        for pid in list(self.players.keys()):
            self._emit_to("intermission_start", self._intermission_snapshot(pid), [pid])

    def _sync_intermission_players(self):
        if not self.intermission:
            return []
        active = [
            sid for sid, player in self.players.items()
            if not player.get("dead")
        ] or list(self.players.keys())
        active_set = set(active)
        self.intermission["players"] = active
        self.intermission["ready"] = [
            sid for sid in self.intermission.get("ready", [])
            if sid in active_set
        ]
        return active

    def _emit_intermission_updates(self, players=None):
        for pid in list(players or self.players.keys()):
            self._emit_to("intermission_start", self._intermission_snapshot(pid), [pid])

    def _try_advance_intermission(self, now=None):
        if not self.intermission:
            return False
        active = self._sync_intermission_players()
        if not active:
            self.intermission = None
            return False
        ready = set(self.intermission.get("ready", []))
        if len(ready) < len(active):
            self._emit_intermission_updates(active)
            return False
        data = self.intermission
        exit_point = dict(data.get("exit") or {})
        players_in_zone = list(data.get("players") or [])
        route_reward = dict(data.get("routeReward") or {})
        self._advance_stage(now or self._now(), exit_point, players_in_zone, route_reward=route_reward)
        return True

    def continue_intermission(self, sid):
        if not self.intermission:
            return False
        active = self._sync_intermission_players()
        if sid not in active:
            return False
        ready = self.intermission.setdefault("ready", [])
        if sid not in ready:
            ready.append(sid)
        self._try_advance_intermission(self._now())
        return True

    def _advance_stage(self, now, exit_point, players_in_zone, route_reward=None):
        self.intermission = None
        cleared_stage = self.wave
        self._emit("wave_clear", {
            "wave": cleared_stage,
            "name": exit_point["name"],
            "x": round(exit_point["x"], 1),
            "y": round(exit_point["y"], 1),
            "sceneId": SCENE_MAIN,
            "boss_next": self._is_boss_wave(cleared_stage + 1),
        })
        self.wave += 1
        self.wave_remaining = self._wave_budget()
        self.infection_source_remaining = self._infection_source_budget()
        self.wave_kills = 0
        self.wave_announced = True
        self.next_fog_wave_at = now + 5.0
        self.fog_active_until = 0.0
        self.pending_fog_spawns.clear()
        self.zombies.clear()
        self.bullets.clear()
        self.items.clear()
        self._gen_obstacles()
        self._start_stage_tasks()
        if self.next_stage_reveal and self.extractions:
            reveal = random.choice(self.extractions)
            reveal["visible"] = True
            reveal["ready_notified"] = self._exit_ready(reveal)
            self.mission = reveal
            self.next_stage_reveal = False
        for sid, player in self.players.items():
            sx, sy = self.safe_player_spawn()
            player["scene"] = SCENE_MAIN
            player["scene_name"] = "设施楼层"
            player["room_id"] = ""
            player["main_x"] = sx
            player["main_y"] = sy
            player["facility_room_id"] = ""
            player["x"] = sx
            player["y"] = sy
            player["vx"] = 0
            player["vy"] = 0
            player["paused"] = False
            player["dead"] = False
            player["lives"] = player.get("max_lives", PLAYER_STAGE_LIVES)
            player["hp"] = min(player["max_hp"], max(player.get("hp", player["max_hp"]), player["max_hp"] * 0.72))
            player["protect_until"] = now + PROTECT
            self._emit_near("p_resp", {
                "pid": sid,
                "x": sx,
                "y": sy,
                "hp": round(player["hp"], 1),
                "lives": player.get("lives", PLAYER_STAGE_LIVES),
                "maxLives": player.get("max_lives", PLAYER_STAGE_LIVES),
            }, sx, sy, include=sid, scene=SCENE_MAIN)
        stage_zombies = min(INITIAL_ZOMBIES + self.wave * 5, self.wave_remaining)
        for _ in range(stage_zombies):
            if self.spawn_zombie(emit=False, pressure=True):
                self.wave_remaining -= 1
        self._spawn_wave_burst()
        for _ in range(INITIAL_ITEMS * self._peak_players):
            self.spawn_item(emit=False)
        if route_reward and route_reward.get("route") == "service":
            for _ in range(min(3, 1 + len(self.players))):
                self.spawn_item(item_type="ammo", emit=False)
        if route_reward and route_reward.get("route") == "security":
            self.spawn_item(item_type="parts", emit=False)
        if route_reward and route_reward.get("route") == "archive":
            self.spawn_item(item_type="shield", emit=False)
            self.spawn_item(item_type="ammo_explosive", emit=False)
        self._emit("wave_start", {
            **self._scene_payload(SCENE_MAIN),
            "wave": self.wave,
            "remaining": self.wave_remaining,
            "boss": self._is_boss_wave(),
            "story": self._story_for_wave(),
            "stage": self.stage_director,
            "routeReward": route_reward,
            "sceneId": SCENE_MAIN,
        })

    def _complete_mission(self, now, exit_point, players_in_zone):
        if not exit_point or exit_point.get("done"):
            return
        exit_point["done"] = True
        exit_point["charge"] = 1.0
        route_reward = self._apply_route_reward(now, exit_point)
        for sid in players_in_zone:
            player = self.players.get(sid)
            if not player or player.get("dead"):
                continue
            player["score"] += MISSION_REWARD_SCORE
            player["xp"] += MISSION_REWARD_XP
            player["lore"] = player.get("lore", 0) + 1
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
                    "sceneId": self._entity_scene(player),
                    "_targets": [sid],
                })
            file_text = CASE_FILES[(player["lore"] - 1) % len(CASE_FILES)]
            self._emit_to("lore_found", {
                "pid": sid,
                "count": player["lore"],
                "text": file_text,
                "col": player["color"],
            }, [sid])
        self._emit("mission_complete", {
            "name": exit_point["name"],
            "x": round(exit_point["x"], 1),
            "y": round(exit_point["y"], 1),
            "sceneId": SCENE_MAIN,
            "players": len(players_in_zone),
            "wave": self.wave,
            "nextWave": self.wave + 1,
            "ending": self._is_final_wave(self.wave),
            "route": route_reward.get("route"),
            "rewardTitle": route_reward.get("rewardTitle"),
            "rewardText": route_reward.get("rewardText"),
            "shortReward": route_reward.get("shortReward"),
            "routeHook": route_reward.get("routeHook"),
            "affected": route_reward.get("affected", 0),
            "amount": route_reward.get("amount", 0),
        })
        self._begin_intermission(now, exit_point, players_in_zone, route_reward)

    def _update_mission(self, dt, now):
        if not self.extractions:
            return
        alive_players = [
            (sid, player) for sid, player in self.players.items()
            if not player.get("dead") and not player.get("paused") and self._entity_scene(player) == SCENE_MAIN
        ]
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
                    "rewardTitle": exit_point.get("rewardTitle", ""),
                    "rewardText": exit_point.get("rewardText", ""),
                    "shortReward": exit_point.get("shortReward", ""),
                    "routeHook": exit_point.get("routeHook", ""),
                    "ready": self._exit_ready(exit_point),
                    "x": round(exit_point["x"], 1),
                    "y": round(exit_point["y"], 1),
                    "col": exit_point["color"],
                }, exit_point["x"], exit_point["y"])
                if not exit_point.get("alarm_spawned"):
                    exit_point["alarm_spawned"] = True
                    self._spawn_pressure_pack(EXTRACTION_REVEAL_SPAWNS + min(5, self.wave), now, urgent=True, allow_infection_source=True)
                    self._trigger_fog_wave(now, reason="terminal", origin=exit_point)

            if exit_point.get("visible") and self._exit_ready(exit_point) and not exit_point.get("ready_notified"):
                exit_point["ready_notified"] = True
                self._emit("exit_ready", {
                    "id": exit_point["id"],
                    "name": exit_point["name"],
                    "requires": exit_point["requires"],
                    "requireText": self._requires_text(exit_point["requires"]),
                    "rewardTitle": exit_point.get("rewardTitle", ""),
                    "rewardText": exit_point.get("rewardText", ""),
                    "shortReward": exit_point.get("shortReward", ""),
                    "routeHook": exit_point.get("routeHook", ""),
                    "x": round(exit_point["x"], 1),
                    "y": round(exit_point["y"], 1),
                    "col": exit_point["color"],
                    "sceneId": SCENE_MAIN,
                })

            players_in_zone = [
                sid for sid, player in alive_players
                if math.hypot(player["x"] - exit_point["x"], player["y"] - exit_point["y"]) <= exit_point["radius"] + PLAYER_R
            ]
            if players_in_zone and self._exit_ready(exit_point):
                exit_point["visible"] = True
                self.mission = exit_point
                if not exit_point.get("charge_fog_spawned"):
                    exit_point["charge_fog_spawned"] = True
                    self._trigger_fog_wave(now, reason="extraction", force=True, origin=exit_point)
                exit_point["charge"] = min(1.0, exit_point.get("charge", 0) + dt * len(players_in_zone) / EXTRACTION_CAPTURE_SECONDS)
                exit_point["charge_spawn"] = exit_point.get("charge_spawn", 0.0) + dt
                if exit_point["charge_spawn"] >= EXTRACTION_CHARGE_SPAWN_DT:
                    exit_point["charge_spawn"] = 0.0
                    count = EXTRACTION_CHARGE_SPAWNS + min(2, len(players_in_zone) - 1) + min(2, self.wave // 4)
                    self._spawn_pressure_pack(count, now, urgent=True, allow_infection_source=True)
            else:
                exit_point["charge"] = max(0, exit_point.get("charge", 0) - dt * 0.08)
                exit_point["charge_spawn"] = 0.0
            if exit_point["charge"] >= 1:
                self._complete_mission(now, exit_point, players_in_zone)
                return

    def _update_zombies(self, dt, now):
        self._room_path_recomputes_this_tick = 0
        alive = [
            p for p in self.players.values()
            if not p.get("dead") and not p.get("paused")
        ]
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
            dist_to_target = math.hypot(dx, dy)
            self._maybe_boss_phase(zid, zombie, now)
            self._maybe_boss_slam(zid, zombie, target, dist_to_target, now)
            if zombie["type"] == "boss":
                speed *= 1 + zombie.get("phase", 0) * 0.24
                if dist_to_target > 520:
                    speed *= 1.18
            speed = self._maybe_leap_speed(zombie, target, speed, dist_to_target, now)
            waypoint = self._zombie_waypoint(zombie, target, now)
            vx, vy, nx, ny, dist = self._steer_zombie(zombie, waypoint, speed, dt, now)
            zombie["target"] = target["id"]
            zombie["vx"] = vx
            zombie["vy"] = vy
            zombie["x"], zombie["y"] = nx, ny
            dist_after = math.hypot(target["x"] - zombie["x"], target["y"] - zombie["y"])
            if dist_after <= zombie["radius"] + target["radius"] + 8:
                meta = ZOMBIE_TYPES.get(zombie["type"], ZOMBIE_TYPES["walker"])
                self._damage_player(
                    target["id"],
                    meta["damage"] * dt,
                    now,
                    zid,
                    source_scene=self._entity_scene(zombie),
                )

    def _director_pressure(self, dt, now):
        if self._pending_fog_spawn_count():
            return
        self.director_timer += dt
        if self.director_timer < DIRECTOR_CHECK_DT:
            return
        self.director_timer = 0.0
        alive = [
            p for p in self.players.values()
            if not p.get("dead") and not p.get("paused") and self._entity_scene(p) == SCENE_MAIN
        ]
        watch_points = alive[:]
        if not watch_points:
            return

        leash_sq = DIRECTOR_LEASH_RADIUS * DIRECTOR_LEASH_RADIUS
        near_sq = ZOMBIE_INTEREST_RADIUS * ZOMBIE_INTEREST_RADIUS
        near_count = 0
        relocated = 0
        main_zombies = 0
        for zid, zombie in list(self.zombies.items()):
            if self._entity_scene(zombie) != SCENE_MAIN:
                continue
            main_zombies += 1
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
            zombie["path"] = None
            zombie["path_target"] = None
            zombie["path_goal"] = None
            zombie["path_time"] = 0
            zombie["path_idx"] = 1
            relocated += 1
            if relocated >= DIRECTOR_MAX_PRESSURE_SPAWNS:
                break

        if len(self.zombies) >= MAX_ZOMBIES:
            return
        source_available = self.infection_source_remaining > 0
        if self.wave_remaining <= 0 and not source_available:
            return
        desired = min(
            DIRECTOR_MAX_NEAR_ZOMBIES,
            max(DIRECTOR_MIN_NEAR_ZOMBIES, max(1, len(alive)) * DIRECTOR_NEAR_ZOMBIES_PER_PLAYER),
        )
        if near_count <= max(3, int(desired * 0.36)) and main_zombies <= desired:
            if self._trigger_fog_wave(now, reason="silence"):
                return
        if self.wave_remaining <= 0:
            return
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
            if self.spawn_zombie(emit=False, pressure=True):
                self.wave_remaining -= 1

    def _spawn_wave_burst(self):
        alive_count = max(1, sum(1 for player in self.players.values() if not player.get("dead") and self._entity_scene(player) == SCENE_MAIN))
        budget = min(
            WAVE_BURST_MAX,
            WAVE_BURST_BASE + alive_count * WAVE_BURST_PER_PLAYER + self.wave * 2,
            self.wave_remaining,
            MAX_ZOMBIES - len(self.zombies),
        )
        scripted = (
            ("runner", 1),
            ("crawler", 1),
            ("brute", 1),
            ("toxic", 1),
            ("armored", 2),
            ("leaper", 2),
            ("stalker", 2),
            ("spitter", 2),
            ("screamer", 3),
            ("bloater", 3),
            ("warden", 4),
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
            zid = self.spawn_zombie(ztype=ztype, emit=False, pressure=True)
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
                        "sceneId": SCENE_MAIN,
                    })

    def _reward_wave_clear(self, now, cleared_wave):
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
        if self._pending_fog_spawn_count():
            return
        spawn_dt = ZOMBIE_SPAWN_DT * (0.72 if self.wave == 1 else 1.0)
        self.zombie_spawn_timer += dt
        if self.zombie_spawn_timer < spawn_dt:
            return
        self.zombie_spawn_timer = 0.0
        alive_count = sum(
            1 for player in self.players.values()
            if not player.get("dead") and not player.get("paused") and self._entity_scene(player) == SCENE_MAIN
        )
        if alive_count <= 0:
            return
        main_zombies = sum(1 for zombie in self.zombies.values() if self._entity_scene(zombie) == SCENE_MAIN)
        target_near = min(DIRECTOR_MAX_NEAR_ZOMBIES, DIRECTOR_MIN_NEAR_ZOMBIES + alive_count * 5 + self.wave * 2)
        budget = min(
            8 + min(6, self.wave),
            max(5, target_near - main_zombies // 2),
            self.wave_remaining,
            MAX_ZOMBIES - len(self.zombies),
        )
        for _ in range(max(0, budget)):
            if self.spawn_zombie(emit=False, pressure=True):
                self.wave_remaining -= 1

    def _maintain_items(self, dt):
        self.item_spawn_timer += dt
        if self.item_spawn_timer < ITEM_SPAWN_DT:
            return
        self.item_spawn_timer = 0.0
        if len(self.items) < max(4, self._max_items // 2):
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
                scene_id = self._entity_scene(player)
                self.remove_player(sid)
                self._emit("p_leave", {"pid": sid, "reason": "timeout", "sceneId": scene_id})

    def _grant_emergency_ammo(self, player):
        if player.get("ammo", 0) + self._ammo_reserve(player) > 0:
            return
        self._add_ammo_reserve(player, ammo_type_for_weapon(player.get("weapon_id", "pistol")), self._weapon_mag_size(player))

    def _respawn_player(self, pid, player, now):
        sx, sy = self.safe_player_spawn()
        old_scene = self._entity_scene(player)
        player["scene"] = SCENE_MAIN
        player["scene_name"] = "设施楼层"
        player["room_id"] = ""
        player["main_x"] = sx
        player["main_y"] = sy
        player["facility_room_id"] = ""
        player["x"] = sx
        player["y"] = sy
        player["vx"] = 0
        player["vy"] = 0
        player["hp"] = player["max_hp"]
        player["dead"] = False
        player["protect_until"] = now + PROTECT
        self._grant_emergency_ammo(player)
        self._sync_weapon_fields(player)
        self._emit_near("p_resp", {
            "pid": pid,
            "x": sx,
            "y": sy,
            "hp": player["hp"],
            "lives": player.get("lives", PLAYER_STAGE_LIVES),
            "maxLives": player.get("max_lives", PLAYER_STAGE_LIVES),
        }, sx, sy, include=pid, scene=SCENE_MAIN)
        if old_scene != SCENE_MAIN:
            self._emit_scene_change(pid, reason="respawn")
            self._sweep_empty_room_scene(old_scene)

    def _restart_current_stage(self, now, reason="wipe"):
        if reason not in STAGE_FAILURE_REASONS:
            raise ValueError(f"unsupported stage failure reason: {reason}")
        self.intermission = None
        self.zombies.clear()
        self.bullets.clear()
        self.items.clear()
        self.wave_remaining = self._wave_budget()
        self.infection_source_remaining = self._infection_source_budget()
        self.wave_kills = 0
        self.next_fog_wave_at = now + 5.0
        self.fog_active_until = 0.0
        self.pending_fog_spawns.clear()
        self._gen_obstacles()
        self._start_stage_tasks()
        for pid, player in self.players.items():
            player["lives"] = player.get("max_lives", PLAYER_STAGE_LIVES)
            player["paused"] = False
            self._respawn_player(pid, player, now)
        stage_zombies = min(INITIAL_ZOMBIES + self.wave * 5, self.wave_remaining)
        for _ in range(stage_zombies):
            if self.spawn_zombie(emit=False, pressure=True):
                self.wave_remaining -= 1
        self._spawn_wave_burst()
        for _ in range(INITIAL_ITEMS * self._peak_players):
            self.spawn_item(emit=False)
        scene_payload = self._scene_payload(SCENE_MAIN)
        # stage_failed reasons: wipe=deployment exhausted, abandon=player chose to restart,
        # extraction_failed=reserved for future terminal-route failures.
        self._emit("stage_failed", {
            **scene_payload,
            "wave": self.wave,
            "reason": reason,
            "lives": PLAYER_STAGE_LIVES,
            "sceneId": SCENE_MAIN,
        })
        self._emit("wave_start", {
            **scene_payload,
            "wave": self.wave,
            "remaining": self.wave_remaining,
            "boss": self._is_boss_wave(),
            "story": self._story_for_wave(),
            "stage": self.stage_director,
            "sceneId": SCENE_MAIN,
        })

    def restart_current_stage(self, sid=None, reason="abandon"):
        if reason not in STAGE_FAILURE_REASONS:
            raise ValueError(f"unsupported stage failure reason: {reason}")
        if not self.running or not self.players:
            return False
        if sid and sid not in self.players:
            return False
        if self.intermission:
            targets = [sid] if sid else list(self.players.keys())
            self._emit_to("stage_restart_denied", {
                "reason": "整备中不能重开本关，先决定是否进入下一层。",
                "col": "#ffc247",
            }, targets)
            return False
        self._restart_current_stage(self._now(), reason=reason)
        return True

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
            if self.intermission:
                for player in self.players.values():
                    player["keys"] = {}
                    player["shooting"] = False
                    player["vx"] = 0
                    player["vy"] = 0
                    player["ack_seq"] = max(player.get("ack_seq", 0), player.get("input_seq", 0))
                    player["protect_until"] = max(player.get("protect_until", 0), now + 3.0)
                return
            self._maintain_zombies(dt, now)
            self._director_pressure(dt, now)
            self._maintain_items(dt)
            self._expire_player_effects(now)
            self._update_players(dt, now)
            self._apply_facility_effects(dt, now)
            self._update_mission(dt, now)
            self._update_zombies(dt, now)
            self._process_pending_fog_spawns(now)
            self._update_bullets(dt, now)
            self._collect_items(now)

            deaths_pending = []
            for pid, player in self.players.items():
                if player.get("dead") and now - player.get("death_time", now) > 2.3:
                    if player.get("lives", 0) > 0:
                        self._respawn_player(pid, player, now)
                    else:
                        deaths_pending.append(pid)
            if deaths_pending and all(player.get("dead") for player in self.players.values()):
                self._restart_current_stage(now, reason="wipe")
        finally:
            self._record_tick_perf(perf_start)

    def add_player(self, sid):
        if sid in self.players:
            player = self.players[sid]
            now = self._now()
            player["last_input"] = now
            player["last_seen"] = now
            return player["idx"], player["x"], player["y"]
        if len(self.players) >= MAX_PLAYERS:
            return None, None, None
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
            "aim_x": None,
            "aim_y": None,
            "shooting": False,
            "fire_cd": 0,
            "melee_cd": 0,
            "last_melee_at": -999,
            "ammo": MAG_SIZE,
            "mag_size": MAG_SIZE,
            "current_reserve": START_AMMO_RESERVE["pistol"],
            "ammo_reserve": dict(START_AMMO_RESERVE),
            "lives": PLAYER_STAGE_LIVES,
            "max_lives": PLAYER_STAGE_LIVES,
            "materials": 0,
            "lore": 0,
            "talents": {},
            "weapon_level": 1,
            "weapon_id": "pistol",
            "weapons": {"pistol": {"ammo": MAG_SIZE}},
            "reload_until": 0,
            "rapid_until": 0,
            "spread_until": 0,
            "shield_until": 0,
            "vehicle_until": 0,
            "vehicle_ram_cd": 0,
            "vehicle_end_notified": False,
            "paused": False,
            "scene": SCENE_MAIN,
            "scene_name": "设施楼层",
            "room_id": "",
            "main_x": sx,
            "main_y": sy,
            "room_enter_cd": 0.0,
            "facility_room_id": "",
            "facility_label": "",
            "facility_status": "",
            "facility_search": 0.0,
            "facility_notice_cd": 0,
            "facility_notice_key": "",
            "facility_notice_repeat_at": 0.0,
            "interact_requested": False,
            "dash_cd": 0,
            "level": 1,
            "xp": 0,
            "combo": 0,
            "combo_until": 0,
            "fire_requested": False,
            "input_seq": 0,
            "ack_seq": 0,
            "idx": idx,
            "keys": {},
            "protect_until": now + PROTECT,
            "last_input": now,
            "last_seen": now,
        }
        self._peak_players = max(self._peak_players, len(self.players))
        return idx, sx, sy

    def remove_player(self, sid):
        removed = sid in self.players
        if removed:
            scene_id = self._entity_scene(self.players[sid])
            del self.players[sid]
            for bid, bullet in list(self.bullets.items()):
                if bullet.get("owner") == sid:
                    self.bullets.pop(bid, None)
            self._sweep_empty_room_scene(scene_id)
            if self.intermission:
                if not self.players:
                    self.intermission = None
                else:
                    self._try_advance_intermission(self._now())
        if not self.players:
            self.pending_fog_spawns.clear()
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
        player["keys"] = inp["keys"]
        player["aim_angle"] = inp["aim_angle"]
        if inp.get("aim_target"):
            player["aim_x"], player["aim_y"] = inp["aim_target"]
            self._refresh_player_aim(player)
        player["paused"] = inp.get("paused", False)
        player["interact_requested"] = bool(inp.get("interact"))
        if self.intermission:
            player["keys"] = {}
            player["shooting"] = False
            player["fire_requested"] = False
            player["interact_requested"] = False
            player["vx"] = 0
            player["vy"] = 0
            player["ack_seq"] = player.get("input_seq", player.get("ack_seq", 0))
            player["last_input"] = now
            player["last_seen"] = now
            return
        if player.get("dead"):
            player["keys"] = {}
            player["shooting"] = False
            player["fire_requested"] = False
            player["interact_requested"] = False
            player["vx"] = 0
            player["vy"] = 0
            player["ack_seq"] = player.get("input_seq", player.get("ack_seq", 0))
            player["last_input"] = now
            player["last_seen"] = now
            return
        if player["paused"]:
            player["keys"] = {}
            player["shooting"] = False
            player["fire_requested"] = False
            player["interact_requested"] = False
            player["vx"] = 0
            player["vy"] = 0
            player["ack_seq"] = player.get("input_seq", player.get("ack_seq", 0))
            player["last_input"] = now
            player["last_seen"] = now
            return
        player["shooting"] = inp["shooting"]
        player["last_input"] = now
        player["last_seen"] = now
        if inp.get("weapon"):
            self._switch_weapon(sid, player, inp["weapon"], now)
        if inp["dash"]:
            self._try_dash(sid, player, now)
        if inp["reload"]:
            self._try_reload(sid, player, now, manual=True)
        if inp["fire"]:
            player["fire_requested"] = True

    def _refresh_player_aim(self, player):
        tx = player.get("aim_x")
        ty = player.get("aim_y")
        if tx is None or ty is None:
            return player.get("aim_angle", 0)
        dx = tx - player["x"]
        dy = ty - player["y"]
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return player.get("aim_angle", 0)
        angle = math.atan2(dy, dx)
        player["aim_angle"] = angle
        return angle

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
        wid, meta, _ = self._sync_weapon_fields(player)
        vehicle_left = max(0, player.get("vehicle_until", 0) - now)
        current_speed = self._player_speed(player, now) * (VEHICLE_SPEED_MULT if vehicle_left > 0 else 1)
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
            round(current_speed, 1),
            player.get("kills", 0),
            now < player.get("spread_until", 0),
            max_hp,
            player.get("ammo", MAG_SIZE),
            player.get("mag_size", MAG_SIZE),
            player.get("current_reserve", self._ammo_reserve(player, ammo_type_for_weapon(wid))),
            player.get("materials", 0),
            player.get("lore", 0),
            player.get("weapon_level", 1),
            round(max(0, player.get("reload_until", 0) - now), 2),
            wid,
            meta.get("name", "手枪"),
            ",".join(self._unlocked_weapon_ids(player)),
            vehicle_left > 0,
            round(vehicle_left, 2),
            player.get("facility_label", ""),
            player.get("facility_status", ""),
            self._ammo_pool_snapshot(player),
            ammo_type_for_weapon(wid),
            AMMO_TYPE_LABELS.get(ammo_type_for_weapon(wid), "备用弹"),
            player.get("lives", PLAYER_STAGE_LIVES),
            player.get("max_lives", PLAYER_STAGE_LIVES),
            self._entity_scene(player),
            player.get("scene_name", "设施楼层"),
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
            bullet.get("weapon", "pistol"),
            round(bullet.get("explosion_radius", 0), 1),
            round(bullet.get("damage", BULLET_DAMAGE), 1),
            round(bullet.get("spawn_x", bullet["x"]), 1),
            round(bullet.get("spawn_y", bullet["y"]), 1),
            round(bullet.get("prev_x", bullet.get("spawn_x", bullet["x"])), 1),
            round(bullet.get("prev_y", bullet.get("spawn_y", bullet["y"])), 1),
            bullet.get("shot_seq", 0),
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
            "sceneId": self._entity_scene(zombie),
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
            "sceneId": self._entity_scene(item),
        }

    def _near_player_tuples(self, sid, viewer, player_tuples):
        candidates = []
        radius_sq = PLAYER_INTEREST_RADIUS * PLAYER_INTEREST_RADIUS
        scene = self._entity_scene(viewer)
        for pid, player in self.players.items():
            if pid == sid:
                candidates.append((0.0, pid))
                continue
            if self._entity_scene(player) != scene:
                continue
            d2 = (player["x"] - viewer["x"]) ** 2 + (player["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((d2, pid))
        if len(candidates) > MAX_SYNC_PLAYERS_PER_CLIENT:
            candidates.sort(key=lambda item: item[0])
            candidates = candidates[:MAX_SYNC_PLAYERS_PER_CLIENT]
        return {pid: player_tuples[pid] for _, pid in candidates if pid in player_tuples}

    def _dynamic_aoi_radius(self, scene_id):
        if scene_id == SCENE_MAIN:
            return DYNAMIC_AOI_RADIUS_MAIN
        scene = self._scene_def(scene_id)
        return scene.get("dynamic_aoi_radius", DYNAMIC_AOI_RADIUS_ROOM)

    def _limited_zombies_near(self, grid, viewer):
        candidates = []
        scene = self._entity_scene(viewer)
        radius = self._dynamic_aoi_radius(scene)
        radius_sq = radius * radius
        for zid, zombie in self._zombies_near(grid, viewer["x"], viewer["y"], radius):
            if self._entity_scene(zombie) != scene:
                continue
            d2 = (zombie["x"] - viewer["x"]) ** 2 + (zombie["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((d2, zid, zombie))
        if len(candidates) > MAX_SYNC_ZOMBIES_PER_CLIENT:
            candidates.sort(key=lambda item: item[0])
            candidates = candidates[:MAX_SYNC_ZOMBIES_PER_CLIENT]
        return {zid: self._zombie_tuple(zombie) for _, zid, zombie in candidates}

    def _limited_bullets_near(self, viewer):
        candidates = []
        scene = self._entity_scene(viewer)
        radius = self._dynamic_aoi_radius(scene)
        radius_sq = radius * radius
        for bid, bullet in self.bullets.items():
            if self._entity_scene(bullet) != scene:
                continue
            if bullet.get("owner") == viewer.get("id"):
                candidates.append((0.0, bid, bullet))
                continue
            d2 = (bullet["x"] - viewer["x"]) ** 2 + (bullet["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((d2, bid, bullet))
        if len(candidates) > MAX_SYNC_BULLETS_PER_CLIENT:
            candidates.sort(key=lambda item: item[0])
            candidates = candidates[:MAX_SYNC_BULLETS_PER_CLIENT]
        return {bid: self._bullet_tuple(bullet) for _, bid, bullet in candidates}

    def _limited_items_near(self, viewer):
        candidates = []
        scene = self._entity_scene(viewer)
        radius = self._dynamic_aoi_radius(scene)
        scene_def = self._scene_def(scene)
        room_objective_radius = math.hypot(scene_def.get("mw", ROOM_W), scene_def.get("mh", ROOM_H))
        for iid, item in self.items.items():
            if self._entity_scene(item) != scene:
                continue
            is_objective = item.get("type") in OBJECTIVE_ITEM_TYPES
            item_radius = room_objective_radius if scene != SCENE_MAIN and is_objective else radius
            radius_sq = item_radius * item_radius
            d2 = (item["x"] - viewer["x"]) ** 2 + (item["y"] - viewer["y"]) ** 2
            if d2 <= radius_sq:
                candidates.append((0 if is_objective else 1, d2, iid, item))
        if len(candidates) > MAX_SYNC_ITEMS_PER_CLIENT:
            candidates.sort(key=lambda item: (item[0], item[1]))
            candidates = candidates[:MAX_SYNC_ITEMS_PER_CLIENT]
        return {iid: self._item_tuple(item) for _, _, iid, item in candidates}

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
            scene_def = self._scene_def(self._entity_scene(viewer))
            players = self._near_player_tuples(sid, viewer, player_tuples)
            zombies = self._limited_zombies_near(zombie_grid, viewer)
            bullets = self._limited_bullets_near(viewer)
            items = self._limited_items_near(viewer)
        else:
            scene_def = self._scene_def(SCENE_MAIN)
            players = player_tuples
            zombies = {zid: self._zombie_tuple(zombie) for zid, zombie in self.zombies.items()}
            bullets = {bid: self._bullet_tuple(bullet) for bid, bullet in self.bullets.items()}
            items = {iid: self._item_tuple(item) for iid, item in self.items.items()}
        return {
            "v": PROTOCOL_VERSION,
            "tick": self.tick_id,
            "time": round(now, 3),
            "scene": scene_def.get("id", SCENE_MAIN),
            "sceneName": scene_def.get("name", "设施楼层"),
            "mw": scene_def.get("mw", MAP_W),
            "mh": scene_def.get("mh", MAP_H),
            "dynamicAoi": self._dynamic_aoi_radius(scene_def.get("id", SCENE_MAIN)),
            "p": players,
            "z": zombies,
            "b": bullets,
            "i": items,
            "zt": self._scene_zombie_count(scene_def.get("id", SCENE_MAIN)),
            "bt": len(self.bullets),
            "it": len(self.items),
            "w": self.wave,
            "wr": self.wave_remaining,
            "wa": self.wave_announced,
            "lb": leaderboard,
            "obj": self._objective_snapshot(full=False),
            "mission": self._mission_snapshot(full=False),
            "exits": self._extractions_snapshot(full=False),
            "intermission": self._intermission_snapshot(sid),
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
        self._record_payload_perf([snap])
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
        self._record_payload_perf([snap for _, snap in packets])
        perf = self._perf_snapshot()
        for _, snap in packets:
            snap["perf"] = perf
        return packets

    def get_init_data(self, sid, idx):
        now = self._now()
        player = self.players.get(sid, {})
        scene_def = self._scene_def(self._entity_scene(player))
        scene_is_main = scene_def.get("id") == SCENE_MAIN
        return {
            "v": PROTOCOL_VERSION,
            "tick": self.tick_id,
            "time": round(now, 3),
            "scene": scene_def.get("id", SCENE_MAIN),
            "sceneName": scene_def.get("name", "设施楼层"),
            "id": sid,
            "col": player_color(idx),
            "nm": player_name(idx),
            "idx": idx,
            "cfg": {
                "gameVersion": GAME_VERSION,
                "playerSpeed": PLAYER_SPD,
                "playerRadius": PLAYER_R,
                "playerMaxHp": PLAYER_MAX_HP,
                "dashDist": DASH_DIST,
                "dashCd": DASH_CD,
                "fireInterval": FIRE_INTERVAL,
                "bulletSpeed": BULLET_SPEED,
                "magSize": MAG_SIZE,
                "maxReserveByType": MAX_RESERVE_BY_TYPE,
                "ammoTypeLabels": AMMO_TYPE_LABELS,
                "stageLives": PLAYER_STAGE_LIVES,
                "reloadSeconds": RELOAD_SECONDS,
                "muzzleForward": MUZZLE_FORWARD,
                "weaponOrder": WEAPON_ORDER,
                "weaponTypes": WEAPON_TYPES,
                "vehicleSeconds": VEHICLE_SECONDS,
                "vehicleSpeedMult": VEHICLE_SPEED_MULT,
                "moveAccel": MOVE_ACCEL,
                "moveDecel": MOVE_DECEL,
                "moveCollisionStep": MOVE_COLLISION_STEP,
                "dynamicAoiMain": DYNAMIC_AOI_RADIUS_MAIN,
                "dynamicAoiRoom": DYNAMIC_AOI_RADIUS_ROOM,
                "serverTickHz": SERVER_TICK_HZ,
                "snapshotHz": SNAPSHOT_HZ,
            },
            "mw": scene_def.get("mw", MAP_W),
            "mh": scene_def.get("mh", MAP_H),
            "dynamicAoi": self._dynamic_aoi_radius(scene_def.get("id", SCENE_MAIN)),
            "obs": self.obstacles if scene_is_main else scene_def.get("obs", []),
            "features": self.map_features if scene_is_main else scene_def.get("features", []),
            "z": self._limited_zombies_near(self._build_grid(self.zombies), player),
            "b": self._limited_bullets_near(player),
            "i": self._limited_items_near(player),
            "pl": {
                pid: self._player_tuple(other, now)
                for pid, other in self.players.items()
                if self._entity_scene(other) == scene_def.get("id", SCENE_MAIN)
            },
            "w": self.wave,
            "wr": self.wave_remaining,
            "lb": self._leaderboard(),
            "stage": self.stage_director,
            "obj": self._objective_snapshot(),
            "mission": self._mission_snapshot() if scene_is_main else None,
            "exits": self._extractions_snapshot() if scene_is_main else [],
            "intermission": self._intermission_snapshot(sid),
        }
