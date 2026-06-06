"""Small geometry and input helpers shared by the server simulation."""

import colorsys
import math

from .config import P_COLORS, P_NAMES


def player_color(idx):
    if idx < len(P_COLORS):
        return P_COLORS[idx]
    hue = (idx * 0.61803398875) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.68, 1.0)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def player_name(idx):
    if idx < len(P_NAMES):
        return P_NAMES[idx]
    return f"防线{idx + 1}"


def pt_in_rect(px, py, rx, ry, rw, rh):
    return rx <= px <= rx + rw and ry <= py <= ry + rh


def circ_rect(cx, cy, cr, rx, ry, rw, rh):
    nx = max(rx, min(cx, rx + rw))
    ny = max(ry, min(cy, ry + rh))
    return (cx - nx) ** 2 + (cy - ny) ** 2 < cr * cr


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def finite_float(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def approach(current, target, step):
    if current < target:
        return min(target, current + step)
    if current > target:
        return max(target, current - step)
    return target


def normalize_input(data):
    data = data or {}
    raw_keys = data.get("keys") or {}
    keys = {
        "up": bool(raw_keys.get("up")),
        "down": bool(raw_keys.get("down")),
        "left": bool(raw_keys.get("left")),
        "right": bool(raw_keys.get("right")),
    }
    aim = finite_float(data.get("aim_angle"), 0.0)
    aim = ((aim + math.pi) % (math.pi * 2)) - math.pi
    try:
        seq = int(data.get("seq", 0))
    except (TypeError, ValueError):
        seq = 0
    weapon = str(data.get("weapon") or "").strip().lower()
    return {
        "keys": keys,
        "aim_angle": aim,
        "shooting": bool(data.get("shooting")),
        "fire": bool(data.get("fire")),
        "dash": bool(data.get("dash")),
        "reload": bool(data.get("reload")),
        "paused": bool(data.get("paused")),
        "weapon": weapon,
        "seq": max(0, seq),
    }
