"""Production-oriented ASGI server for Zombie Crisis.

The game simulation remains server authoritative. Socket.IO runs on ASGI so
WebSocket connections are handled by asyncio instead of one thread per client.
"""
import asyncio
import time
from pathlib import Path

import socketio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from server_game.config import SERVER_DT, SNAPSHOT_DT
from server_game.simulation import Game, SCENE_MAIN


BASE_DIR = Path(__file__).resolve().parent

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    ping_interval=5,
    ping_timeout=10,
    transports=["websocket"],
)

http_app = FastAPI(title="僵尸危机")
http_app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_pending_events = []


def queue_emit(event, data):
    _pending_events.append((event, data))


G = Game(emitter=queue_emit)
G.load_save()
_tasks_started = False
_tasks_lock = asyncio.Lock()
_game_lock = asyncio.Lock()
_last_save_at = time.monotonic()
_SAVE_INTERVAL = 60.0


def drain_events():
    events = list(_pending_events)
    _pending_events.clear()
    return events


async def emit_events(events):
    for event, data in events:
        targets = None
        payload = data
        if isinstance(data, dict) and data.get("_targets"):
            targets = list(data.get("_targets") or [])
            payload = dict(data)
            payload.pop("_targets", None)
        if targets:
            await asyncio.gather(*(sio.emit(event, payload, to=pid) for pid in targets))
        else:
            await sio.emit(event, payload)


async def logic_loop():
    """Fixed-rate authoritative simulation loop."""
    global _last_save_at
    while True:
        await sio.sleep(SERVER_DT)
        async with _game_lock:
            G.tick(SERVER_DT)
            events = drain_events()
        await emit_events(events)
        now = time.monotonic()
        if G.running and G.players and now - _last_save_at >= _SAVE_INTERVAL:
            _last_save_at = now
            G.save_state()


async def sync_loop():
    """Send per-player area-of-interest snapshots."""
    while True:
        await sio.sleep(SNAPSHOT_DT)
        async with _game_lock:
            if not G.running or not G.players:
                continue
            packets = G.get_snapshots_by_player()
            wave_announced = G.wave_announced
            if wave_announced:
                G.wave_announced = False
            events = drain_events()
        await emit_events(events)
        started = time.perf_counter()
        await asyncio.gather(*(sio.emit("sync", snap, to=pid) for pid, snap in packets))
        elapsed = (time.perf_counter() - started) * 1000
        old = G.perf.get("sync_ms", 0.0)
        G.perf["sync_ms"] = elapsed if old <= 0 else old * 0.85 + elapsed * 0.15


async def start_background_tasks():
    global _tasks_started
    async with _tasks_lock:
        if _tasks_started:
            return
        _tasks_started = True
        sio.start_background_task(logic_loop)
        sio.start_background_task(sync_loop)


@http_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@sio.event
async def connect(sid, environ, auth=None):
    return True


@sio.event
async def disconnect(sid, reason=None):
    async with _game_lock:
        scene_id = G._entity_scene(G.players[sid]) if sid in G.players else SCENE_MAIN
        removed = G.remove_player(sid)
        events = drain_events()
    await emit_events(events)
    if removed:
        await sio.emit("p_leave", {"pid": sid, "sceneId": scene_id})


@sio.on("join_game")
async def on_join(sid, data):
    await start_background_tasks()
    async with _game_lock:
        if not G.running:
            G.reset()
            G.emit = queue_emit

        idx, sx, sy = G.add_player(sid)
        if idx is None:
            events = drain_events()
        else:
            G.running = True
            init_data = G.get_init_data(sid, idx)
            player = G.players[sid]
            join_data = {
                "pid": sid,
                "x": sx,
                "y": sy,
                "col": player["color"],
                "nm": player["name"],
            }
            events = drain_events()
    if idx is None:
        await emit_events(events)
        await sio.emit("join_error", {"reason": "full"}, to=sid)
        return
    await emit_events(events)
    await sio.emit("init", init_data, to=sid)
    await sio.emit("p_join", join_data, to=sid)


@sio.on("player_input")
async def on_input(sid, data):
    async with _game_lock:
        G.handle_input(sid, data)
        events = drain_events()
    await emit_events(events)


@sio.on("request_scene")
async def on_request_scene(sid, data):
    async with _game_lock:
        G.refresh_scene(sid)
        events = drain_events()
    await emit_events(events)


@sio.on("client_ping")
async def on_client_ping(sid, data):
    data = data or {}
    async with _game_lock:
        G.mark_seen(sid)
    await sio.emit(
        "server_pong",
        {"seq": data.get("seq"), "t": data.get("t")},
        to=sid,
    )


@sio.on("continue_stage")
async def on_continue_stage(sid, data):
    async with _game_lock:
        G.continue_intermission(sid)
        events = drain_events()
    await emit_events(events)


@sio.on("buy_talent")
async def on_buy_talent(sid, data):
    data = data or {}
    async with _game_lock:
        G.buy_talent(sid, data.get("talent"))
        events = drain_events()
    await emit_events(events)


@sio.on("restart_game")
async def on_restart(sid, data):
    await start_background_tasks()
    async with _game_lock:
        G.reset(keep_players=True)
        G.emit = queue_emit
        if sid not in G.players:
            G.add_player(sid)
        G.running = True
        init_packets = [(pid, G.get_init_data(pid, p["idx"])) for pid, p in G.players.items()]
        events = drain_events()
    await emit_events(events)
    for pid, init_data in init_packets:
        await sio.emit("init", init_data, to=pid)
    await sio.emit("game_restart", {})


@sio.on("restart_stage")
async def on_restart_stage(sid, data):
    await start_background_tasks()
    async with _game_lock:
        G.restart_current_stage(sid, reason="abandon")
        events = drain_events()
    await emit_events(events)


asgi_app = socketio.ASGIApp(sio, other_asgi_app=http_app)


if __name__ == "__main__":
    import uvicorn

    print("=== 僵尸危机 ASGI production server ===")
    print("Open http://localhost:8080")
    uvicorn.run(asgi_app, host="0.0.0.0", port=8080, log_level="info", access_log=False)
