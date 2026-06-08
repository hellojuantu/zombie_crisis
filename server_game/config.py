"""Authoritative tuning constants for Zombie Crisis."""

from pathlib import Path


def _read_game_version():
    try:
        version = (Path(__file__).resolve().parent.parent / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0-dev"
    return version or "0.0.0-dev"


GAME_VERSION = _read_game_version()
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
MOVE_COLLISION_STEP = 14.0

PROTOCOL_VERSION = 18
SERVER_TICK_HZ = 30
SERVER_DT = 1 / SERVER_TICK_HZ
SNAPSHOT_HZ = 20
SNAPSHOT_DT = 1 / SNAPSHOT_HZ
INPUT_IDLE_TIMEOUT = 0.55
PLAYER_STALE_TIMEOUT = 5.0
MAX_PLAYERS_SOFT = 100

SPATIAL_CELL = 150
INTEREST_RADIUS = 1450
PLAYER_INTEREST_RADIUS = 980
ZOMBIE_INTEREST_RADIUS = 980
DYNAMIC_AOI_RADIUS_MAIN = 980
DYNAMIC_AOI_RADIUS_ROOM = 520
EVENT_INTEREST_RADIUS = 1080
MAX_SYNC_PLAYERS_PER_CLIENT = 32
MAX_SYNC_ZOMBIES_PER_CLIENT = 56
MAX_SYNC_BULLETS_PER_CLIENT = 28
MAX_SYNC_ITEMS_PER_CLIENT = 16
LEADERBOARD_SIZE = 8

BULLET_SPEED = 760
BULLET_LIFE = 0.9
BULLET_R = 4.2
BULLET_DAMAGE = 26
MUZZLE_FORWARD = 34
FIRE_INTERVAL = 0.145
RAPID_FIRE_MULT = 0.58
SPREAD_ANGLE = 0.16
MAX_BULLETS = 460
MELEE_RANGE = 64
MELEE_AUTO_RANGE = 52
MELEE_ARC = 1.65
MELEE_DAMAGE = 34
MELEE_COOLDOWN = 0.48
MELEE_KNOCKBACK = 46
MAG_SIZE = 24
MAX_PISTOL_RESERVE = 168
START_PISTOL_AMMO = 108
PLAYER_STAGE_LIVES = 3
AMMO_TYPE_LABELS = {
    "pistol": "手枪弹",
    "rifle": "步枪弹",
    "smg": "冲锋枪弹",
    "shell": "霰弹",
    "explosive": "爆破弹",
}
START_AMMO_RESERVE = {
    "pistol": START_PISTOL_AMMO,
    "rifle": 0,
    "smg": 0,
    "shell": 0,
    "explosive": 0,
}
MAX_RESERVE_BY_TYPE = {
    "pistol": MAX_PISTOL_RESERVE,
    "rifle": 108,
    "smg": 216,
    "shell": 42,
    "explosive": 4,
}
AMMO_PICKUP_BY_TYPE = {
    "pistol": (18, 32),
    "rifle": (12, 22),
    "smg": (28, 46),
    "shell": (5, 9),
    "explosive": (1, 2),
}
RELOAD_SECONDS = 1.15
AMMO_PICKUP_MIN = 16
AMMO_PICKUP_MAX = 30
MATERIAL_PICKUP_MIN = 1
MATERIAL_PICKUP_MAX = 3
WEAPON_PARTS_PER_UPGRADE = 4
WEAPON_MAX_LEVEL = 8
WEAPON_ORDER = ["pistol", "rifle", "shotgun", "smg", "launcher"]
WEAPON_TYPES = {
    "pistol": {
        "name": "手枪",
        "mag_size": 24,
        "fire_interval": 0.145,
        "reload_seconds": 1.15,
        "bullet_speed": 760,
        "bullet_life": 0.9,
        "bullet_radius": 4.2,
        "damage": 26,
        "pellets": 1,
        "spread": 0.0,
        "ammo_cost": 1,
        "ammo_type": "pistol",
        "unlock_reserve": 0,
        "muzzle": 34,
        "color": "#dce7f1",
        "explosion_radius": 0,
        "pierce": 0,
    },
    "rifle": {
        "name": "步枪",
        "mag_size": 24,
        "fire_interval": 0.18,
        "reload_seconds": 1.25,
        "bullet_speed": 940,
        "bullet_life": 1.05,
        "bullet_radius": 4.4,
        "damage": 42,
        "pellets": 1,
        "spread": 0.035,
        "ammo_cost": 1,
        "ammo_type": "rifle",
        "unlock_reserve": 28,
        "muzzle": 44,
        "color": "#8fd0ff",
        "explosion_radius": 0,
        "pierce": 1,
    },
    "shotgun": {
        "name": "散弹枪",
        "mag_size": 8,
        "fire_interval": 0.62,
        "reload_seconds": 1.35,
        "bullet_speed": 720,
        "bullet_life": 0.48,
        "bullet_radius": 4.6,
        "damage": 17,
        "pellets": 7,
        "spread": 0.38,
        "ammo_cost": 1,
        "ammo_type": "shell",
        "unlock_reserve": 10,
        "muzzle": 35,
        "color": "#ffc247",
        "explosion_radius": 0,
        "pierce": 0,
    },
    "smg": {
        "name": "冲锋枪",
        "mag_size": 36,
        "fire_interval": 0.068,
        "reload_seconds": 1.2,
        "bullet_speed": 760,
        "bullet_life": 0.72,
        "bullet_radius": 3.6,
        "damage": 16,
        "pellets": 1,
        "spread": 0.095,
        "ammo_cost": 1,
        "ammo_type": "smg",
        "unlock_reserve": 72,
        "muzzle": 32,
        "color": "#48f0a0",
        "explosion_radius": 0,
        "pierce": 0,
    },
    "launcher": {
        "name": "爆破枪",
        "mag_size": 2,
        "fire_interval": 0.86,
        "reload_seconds": 1.75,
        "bullet_speed": 500,
        "bullet_life": 1.05,
        "bullet_radius": 7.2,
        "damage": 22,
        "pellets": 1,
        "spread": 0.02,
        "ammo_cost": 1,
        "ammo_type": "explosive",
        "unlock_reserve": 0,
        "muzzle": 44,
        "color": "#ff8844",
        "explosion_radius": 118,
        "explosion_damage": 52,
        "boss_damage_mult": 0.38,
        "pierce": 0,
    },
}
VEHICLE_SECONDS = 10.0
VEHICLE_SPEED_MULT = 1.52
VEHICLE_RAM_DAMAGE = 76
VEHICLE_RAM_COOLDOWN = 0.34
FACILITY_SEARCH_SECONDS = 2.25
FACILITY_MED_HEAL_PER_SEC = 8
FACILITY_TOXIC_DAMAGE_PER_SEC = 8

MAX_ZOMBIES = 220
INITIAL_ZOMBIES = 48
ZOMBIE_SPAWN_DT = 0.12
WAVE_BASE = 92
WAVE_STEP = 24
ZOMBIE_ATTACK_RANGE = 8
PRESSURE_SPAWN_MIN_DIST = 560
PRESSURE_SPAWN_MAX_DIST = 900
WAVE_BURST_BASE = 24
WAVE_BURST_PER_PLAYER = 6
WAVE_BURST_MAX = 62
BOSS_WAVE_INTERVAL = 3
CAMPAIGN_FINAL_WAVE = 6
DIRECTOR_CHECK_DT = 1.05
DIRECTOR_LEASH_RADIUS = 1680
DIRECTOR_LEASH_AFTER = 4.5
DIRECTOR_MIN_NEAR_ZOMBIES = 18
DIRECTOR_NEAR_ZOMBIES_PER_PLAYER = 6
DIRECTOR_MAX_NEAR_ZOMBIES = 54
DIRECTOR_MAX_PRESSURE_SPAWNS = 8
FOG_WAVE_COOLDOWN = 16.0
FOG_WAVE_COUNT_BASE = 10
FOG_WAVE_COUNT_PER_PLAYER = 5
FOG_WAVE_MAX = 28
FOG_WAVE_MIN_DIST = 360
FOG_WAVE_MAX_DIST = 760
FOG_SPAWNS_PER_TICK = 3
ROOM_FOG_SPAWNS_PER_TICK = 2
ROOM_FOG_WAVE_BASE = 6
ROOM_FOG_WAVE_MAX = 14
ROOM_FOG_PRESSURE_BONUS_REASONS = frozenset(("lab", "security", "morgue", "extraction"))
INFECTION_SOURCE_BASE = 34
INFECTION_SOURCE_STEP = 8
INFECTION_SOURCE_MAX = 96
ZOMBIE_STUCK_EPS = 1.1
ZOMBIE_STUCK_AFTER = 0.35
PATHFIND_INTERVAL = 0.5
PATHFIND_STUCK_REPATH_SECONDS = 0.22
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
BLOATER_ZOMBIE_DAMAGE = 38

MAZE_COLS = 11
MAZE_ROWS = 11
MAZE_CELL = 280
MAZE_WALL = 42
MAZE_SAFE_JITTER = 62
MAZE_EXTRA_LINKS = 8

MISSION_CAPTURE_RADIUS = 78
MISSION_CAPTURE_SECONDS = 3.8
MISSION_DISCOVER_RADIUS = 420
EXTRACTION_COUNT = 4
EXTRACTION_CAPTURE_SECONDS = 3.2
EXTRACTION_DISCOVER_RADIUS = 460
TASK_PICKUPS_PER_STAGE = 5
TASK_DROP_CHANCE = 0.34
EXTRACTION_REVEAL_SPAWNS = 6
EXTRACTION_CHARGE_SPAWN_DT = 1.05
EXTRACTION_CHARGE_SPAWNS = 2
MISSION_MIN_DIST = 460
MISSION_MAX_DIST = 820
MISSION_REWARD_SCORE = 55
MISSION_REWARD_XP = 32
MISSION_REPAIR_AMOUNT = 115

MAX_ITEMS = 7
INITIAL_ITEMS = 1
ITEM_R = 15
ITEM_SPAWN_DT = 13.5
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
        "color": "#b8b09d",
        "weight": 10,
        "unlock": 1,
    },
    "runner": {
        "hp": 32,
        "speed": 158,
        "radius": 13,
        "damage": 12,
        "score": 16,
        "color": "#d0b38d",
        "weight": 4,
        "unlock": 1,
    },
    "crawler": {
        "hp": 26,
        "speed": 178,
        "radius": 11,
        "damage": 9,
        "score": 18,
        "color": "#7b8b8e",
        "weight": 3,
        "unlock": 1,
    },
    "shade": {
        "hp": 42,
        "speed": 146,
        "radius": 14,
        "damage": 16,
        "score": 26,
        "color": "#d6eceb",
        "weight": 2,
        "unlock": 1,
    },
    "brute": {
        "hp": 132,
        "speed": 72,
        "radius": 24,
        "damage": 28,
        "score": 38,
        "color": "#8a5b4a",
        "weight": 2,
        "unlock": 1,
    },
    "toxic": {
        "hp": 62,
        "speed": 92,
        "radius": 17,
        "damage": 20,
        "score": 22,
        "color": "#9db64b",
        "weight": 2,
        "unlock": 1,
    },
    "armored": {
        "hp": 188,
        "speed": 58,
        "radius": 25,
        "damage": 34,
        "score": 55,
        "color": "#8f98a3",
        "weight": 2,
        "unlock": 2,
    },
    "leaper": {
        "hp": 54,
        "speed": 116,
        "radius": 15,
        "damage": 18,
        "score": 32,
        "color": "#c88b61",
        "weight": 2,
        "unlock": 2,
    },
    "screamer": {
        "hp": 72,
        "speed": 86,
        "radius": 18,
        "damage": 12,
        "score": 44,
        "color": "#b68abf",
        "weight": 1,
        "unlock": 3,
    },
    "bloater": {
        "hp": 118,
        "speed": 66,
        "radius": 23,
        "damage": 24,
        "score": 46,
        "color": "#b8694a",
        "weight": 1,
        "unlock": 3,
    },
    "stalker": {
        "hp": 66,
        "speed": 192,
        "radius": 13,
        "damage": 19,
        "score": 34,
        "color": "#cfd2ff",
        "weight": 2,
        "unlock": 2,
    },
    "spitter": {
        "hp": 58,
        "speed": 82,
        "radius": 15,
        "damage": 15,
        "score": 36,
        "color": "#7fdc71",
        "weight": 2,
        "unlock": 2,
    },
    "warden": {
        "hp": 285,
        "speed": 82,
        "radius": 29,
        "damage": 42,
        "score": 86,
        "color": "#b7a0ff",
        "weight": 1,
        "unlock": 4,
    },
    "boss": {
        "hp": 2400,
        "speed": 86,
        "radius": 43,
        "damage": 58,
        "score": 560,
        "color": "#d9445f",
        "weight": 0,
        "unlock": 3,
    },
}

ITEM_TYPES = {
    "rapid": {"color": "#44ffaa", "icon": "R", "name": "速射", "weight": 2},
    "spread": {"color": "#ffcc44", "icon": "3", "name": "三连发", "weight": 2},
    "shield": {"color": "#ffffff", "icon": "S", "name": "护盾", "weight": 1},
    "medkit": {"color": "#ff6688", "icon": "+", "name": "医疗包", "weight": 2},
    "ammo": {"color": "#dce7f1", "icon": "A", "name": "弹药包", "weight": 2},
    "ammo_pistol": {"color": "#dce7f1", "icon": "9", "name": "手枪弹药", "weight": 0, "ammo_type": "pistol"},
    "ammo_rifle": {"color": "#8fd0ff", "icon": "AR", "name": "步枪弹药", "weight": 0, "ammo_type": "rifle"},
    "ammo_smg": {"color": "#48f0a0", "icon": "SM", "name": "冲锋枪弹药", "weight": 0, "ammo_type": "smg"},
    "ammo_shell": {"color": "#ffc247", "icon": "SG", "name": "霰弹药", "weight": 0, "ammo_type": "shell"},
    "ammo_explosive": {"color": "#ff8844", "icon": "EX", "name": "爆破弹药", "weight": 0, "ammo_type": "explosive"},
    "parts": {"color": "#8fd0ff", "icon": "P", "name": "武器零件", "weight": 2},
    "nuke": {"color": "#ff8844", "icon": "!", "name": "清场炸弹", "weight": 1},
    "weapon_rifle": {"color": "#8fd0ff", "icon": "AR", "name": "步枪箱", "weight": 0, "weapon": "rifle"},
    "weapon_shotgun": {"color": "#ffc247", "icon": "SG", "name": "散弹枪箱", "weight": 0, "weapon": "shotgun"},
    "weapon_smg": {"color": "#48f0a0", "icon": "SMG", "name": "冲锋枪箱", "weight": 0, "weapon": "smg"},
    "weapon_launcher": {"color": "#ff8844", "icon": "EX", "name": "爆破枪箱", "weight": 0, "weapon": "launcher"},
    "vehicle": {"color": "#ffc247", "icon": "V", "name": "维修推车", "weight": 0},
    "fuse": {"color": "#66d9ff", "icon": "F", "name": "保险丝", "weight": 0, "task": True},
    "sample": {"color": "#b7ff47", "icon": "V", "name": "病毒样本", "weight": 0, "task": True},
    "keycard": {"color": "#d98cff", "icon": "K", "name": "门禁卡", "weight": 0, "task": True},
    "lore": {"color": "#aee6ff", "icon": "D", "name": "档案碎片", "weight": 0},
}

STORY_BEATS = [
    "第 {wave} 关：耳机里只剩呼吸声，撤离门藏在黑暗深处。",
    "墙后有东西在拖行，别在同一条走廊停太久。",
    "应急灯一闪一灭，地图结构已经和上一层完全不同。",
    "地面有新鲜抓痕，撤离点附近一定有更重的东西。",
    "广播重复着不存在的坐标，真正的出口不会主动暴露。",
    "设施深处传来尖叫，尸群正在向脚步声聚拢。",
    "血雾从通风管漏下来，补给越来越少。",
    "铁门还没开完，撑住最后几秒，不要回头。",
    "墙上的门牌开始重复，说明你已经被设施记住了。",
    "下一层没有安全屋，只有三条互相矛盾的撤离记录。",
    "有个频道一直喊你的名字，但队伍里没人听见。",
    "档案碎片越完整，设施越不想让你离开。",
]

CASE_FILES = [
    "档案 01：第一批撤离名单被人为删除，剩下的人不是被遗忘，而是被筛选。",
    "档案 02：设施墙体会重组，像是在把幸存者赶向同一个房间。",
    "档案 03：样本不是解药，是门禁系统判断你还像不像人的钥匙。",
    "档案 04：黑墙巨像身上的编号，和地下实验室主管的门牌一致。",
    "档案 05：广播里的求救声来自未来 9 分钟后的你自己。",
    "档案 06：真正的撤离点从不发光，它只在你弹尽时开门。",
    "档案 07：安保电梯只向下运行，系统日志却显示它已经抵达地面。",
    "档案 08：维修通道里堆满弹药，像有人提前知道你会走这条路。",
    "档案 09：净化闸门扫描到的不是病毒，而是记忆缺口。",
    "档案 10：样本编号和幸存者腕带一致，感染可能从撤离开始。",
    "档案 11：每次重组楼层，都会多出一间没有门的观察室。",
    "档案 12：最终出口需要一段从未播出的录音作为钥匙。",
]
