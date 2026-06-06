"""Authoritative tuning constants for Zombie Crisis."""

MAP_W = 3400
MAP_H = 3400

PLAYER_R = 17
PLAYER_SPD = 315
PLAYER_MAX_HP = 100
MOVE_ACCEL = 1900
MOVE_DECEL = 2400
PROTECT = 2.0
DASH_DIST = 112
DASH_CD = 1.15

PROTOCOL_VERSION = 9
SERVER_TICK_HZ = 30
SERVER_DT = 1 / SERVER_TICK_HZ
SNAPSHOT_HZ = 16
SNAPSHOT_DT = 1 / SNAPSHOT_HZ
INPUT_IDLE_TIMEOUT = 0.55
PLAYER_STALE_TIMEOUT = 5.0
MAX_PLAYERS_SOFT = 100

SPATIAL_CELL = 150
INTEREST_RADIUS = 1450
PLAYER_INTEREST_RADIUS = 980
ZOMBIE_INTEREST_RADIUS = 980
BULLET_INTEREST_RADIUS = 880
ITEM_INTEREST_RADIUS = 980
EVENT_INTEREST_RADIUS = 1080
MAX_SYNC_PLAYERS_PER_CLIENT = 32
MAX_SYNC_ZOMBIES_PER_CLIENT = 72
MAX_SYNC_BULLETS_PER_CLIENT = 48
MAX_SYNC_ITEMS_PER_CLIENT = 16
LEADERBOARD_SIZE = 8

BULLET_SPEED = 760
BULLET_LIFE = 0.9
BULLET_R = 4.2
BULLET_DAMAGE = 26
FIRE_INTERVAL = 0.145
RAPID_FIRE_MULT = 0.58
SPREAD_ANGLE = 0.16
MAX_BULLETS = 460

MAX_ZOMBIES = 220
INITIAL_ZOMBIES = 42
ZOMBIE_SPAWN_DT = 0.18
WAVE_BASE = 58
WAVE_STEP = 18
ZOMBIE_ATTACK_RANGE = 8
PRESSURE_SPAWN_MIN_DIST = 560
PRESSURE_SPAWN_MAX_DIST = 900
WAVE_BURST_BASE = 18
WAVE_BURST_PER_PLAYER = 5
WAVE_BURST_MAX = 54
BOSS_WAVE_INTERVAL = 5
DIRECTOR_CHECK_DT = 1.05
DIRECTOR_LEASH_RADIUS = 1680
DIRECTOR_LEASH_AFTER = 4.5
DIRECTOR_MIN_NEAR_ZOMBIES = 10
DIRECTOR_NEAR_ZOMBIES_PER_PLAYER = 3
DIRECTOR_MAX_NEAR_ZOMBIES = 46
DIRECTOR_MAX_PRESSURE_SPAWNS = 6
ZOMBIE_STUCK_EPS = 1.1
ZOMBIE_STUCK_AFTER = 0.35
LEAPER_MIN_RANGE = 220
LEAPER_MAX_RANGE = 620
LEAPER_SPEED_MULT = 2.7
LEAPER_COOLDOWN = 2.15
SCREAMER_RADIUS = 290
SCREAMER_COOLDOWN = 4.0
SCREAMER_RALLY_SECONDS = 2.8
SCREAMER_RALLY_MULT = 1.22
BLOATER_RADIUS = 150
BLOATER_PLAYER_DAMAGE = 24
BLOATER_BASE_DAMAGE = 50
BLOATER_ZOMBIE_DAMAGE = 38

BASE_X = MAP_W // 2
BASE_Y = MAP_H // 2
BASE_R = 54
BASE_MAX_HP = 900
BASE_REPAIR_PER_WAVE = 170
BASE_REPAIR_PER_PLAYER = 18
BASE_DAMAGE_ALERT_CD = 0.85
BASE_REVIVE_DELAY = 5.0
BASE_REVIVE_HP_PCT = 0.38
BASE_OBSTACLE_CLEARANCE = 185
BASE_TARGET_BIAS = 0.72

MAZE_COLS = 11
MAZE_ROWS = 11
MAZE_CELL = 280
MAZE_WALL = 42
MAZE_SAFE_JITTER = 62
MAZE_EXTRA_LINKS = 16

MISSION_CAPTURE_RADIUS = 78
MISSION_CAPTURE_SECONDS = 3.8
MISSION_DISCOVER_RADIUS = 420
EXTRACTION_COUNT = 3
EXTRACTION_CAPTURE_SECONDS = 3.2
EXTRACTION_DISCOVER_RADIUS = 460
TASK_PICKUPS_PER_STAGE = 5
TASK_DROP_CHANCE = 0.42
MISSION_MIN_DIST = 460
MISSION_MAX_DIST = 820
MISSION_REWARD_SCORE = 55
MISSION_REWARD_XP = 32
MISSION_REPAIR_AMOUNT = 115

MAX_ITEMS = 10
INITIAL_ITEMS = 3
ITEM_R = 15
ITEM_SPAWN_DT = 7.5
NUKE_RADIUS = 440

LEVEL_XP_BASE = 90
COMBO_WINDOW = 3.6
COMBO_RAPID_BONUS_AT = 10
COMBO_SPREAD_BONUS_AT = 20
COMBO_SHIELD_BONUS_AT = 30

P_COLORS = ["#4da3ff", "#ff5b61", "#4ee483", "#ffc247"]
P_NAMES = ["蓝色游骑", "红色火线", "绿色守望", "金色防线"]

ZOMBIE_TYPES = {
    "walker": {
        "hp": 46,
        "speed": 104,
        "radius": 16,
        "damage": 15,
        "score": 12,
        "color": "#6bd36b",
        "weight": 10,
        "unlock": 1,
    },
    "runner": {
        "hp": 32,
        "speed": 158,
        "radius": 13,
        "damage": 12,
        "score": 16,
        "color": "#9dff7a",
        "weight": 4,
        "unlock": 1,
    },
    "crawler": {
        "hp": 26,
        "speed": 178,
        "radius": 11,
        "damage": 9,
        "score": 18,
        "color": "#7bdcff",
        "weight": 3,
        "unlock": 2,
    },
    "brute": {
        "hp": 132,
        "speed": 72,
        "radius": 24,
        "damage": 28,
        "score": 38,
        "color": "#8a6a4a",
        "weight": 2,
        "unlock": 2,
    },
    "toxic": {
        "hp": 62,
        "speed": 92,
        "radius": 17,
        "damage": 20,
        "score": 22,
        "color": "#c4ff43",
        "weight": 2,
        "unlock": 3,
    },
    "armored": {
        "hp": 188,
        "speed": 58,
        "radius": 25,
        "damage": 34,
        "score": 55,
        "color": "#a9b1bc",
        "weight": 2,
        "unlock": 4,
    },
    "leaper": {
        "hp": 54,
        "speed": 116,
        "radius": 15,
        "damage": 18,
        "score": 32,
        "color": "#ffb347",
        "weight": 2,
        "unlock": 5,
    },
    "screamer": {
        "hp": 72,
        "speed": 86,
        "radius": 18,
        "damage": 12,
        "score": 44,
        "color": "#d88cff",
        "weight": 1,
        "unlock": 6,
    },
    "bloater": {
        "hp": 118,
        "speed": 66,
        "radius": 23,
        "damage": 24,
        "score": 46,
        "color": "#ff8f52",
        "weight": 1,
        "unlock": 7,
    },
    "boss": {
        "hp": 720,
        "speed": 60,
        "radius": 34,
        "damage": 42,
        "score": 220,
        "color": "#ff4d7a",
        "weight": 0,
        "unlock": 5,
    },
}

ITEM_TYPES = {
    "rapid": {"color": "#44ffaa", "icon": "R", "name": "速射", "weight": 4},
    "spread": {"color": "#ffcc44", "icon": "3", "name": "三连发", "weight": 3},
    "shield": {"color": "#ffffff", "icon": "S", "name": "护盾", "weight": 3},
    "medkit": {"color": "#ff6688", "icon": "+", "name": "医疗包", "weight": 4},
    "nuke": {"color": "#ff8844", "icon": "!", "name": "清场炸弹", "weight": 1},
    "fuse": {"color": "#66d9ff", "icon": "F", "name": "保险丝", "weight": 0, "task": True},
    "sample": {"color": "#b7ff47", "icon": "V", "name": "病毒样本", "weight": 0, "task": True},
    "keycard": {"color": "#d98cff", "icon": "K", "name": "门禁卡", "weight": 0, "task": True},
}

STORY_BEATS = [
    "第 {wave} 关：耳机里只剩呼吸声，撤离门藏在黑暗深处。",
    "墙后有东西在拖行，别在同一条走廊停太久。",
    "应急灯一闪一灭，地图结构已经和上一层完全不同。",
    "地面有新鲜抓痕，撤离点附近一定有更重的东西。",
    "广播重复着不存在的坐标，真正的出口不会主动暴露。",
    "迷宫深处传来尖叫，尸群正在向脚步声聚拢。",
    "血雾从通风管漏下来，补给越来越少。",
    "铁门还没开完，撑住最后几秒，不要回头。",
]
