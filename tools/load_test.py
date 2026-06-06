#!/usr/bin/env python3
"""Socket.IO load test for Zombie Crisis.

Example:
    python3 tools/load_test.py --clients 100 --duration 30
"""
import argparse
import asyncio
import math
import statistics
import time

import socketio


async def run_client(index, args):
    client = socketio.AsyncClient(
        reconnection=False,
        logger=False,
        engineio_logger=False,
    )
    joined = asyncio.Event()
    metrics = {
        "connected": False,
        "joined": False,
        "sync": 0,
        "errors": 0,
        "rtt": [],
    }
    ping_sent = {}
    ping_seq = 0

    @client.event
    async def connect():
        metrics["connected"] = True
        await client.emit("join_game", {})

    @client.on("init")
    async def on_init(data):
        metrics["joined"] = True
        joined.set()

    @client.on("sync")
    async def on_sync(data):
        metrics["sync"] += 1

    @client.on("server_pong")
    async def on_server_pong(data):
        sent = ping_sent.pop(data.get("seq"), None)
        if sent:
            metrics["rtt"].append((time.perf_counter() - sent) * 1000)

    try:
        await client.connect(
            args.url,
            transports=["websocket"],
            socketio_path="socket.io",
            wait_timeout=args.connect_timeout,
        )
        await asyncio.wait_for(joined.wait(), timeout=args.connect_timeout)
        started = time.perf_counter()
        end_at = started + args.duration
        next_ping = started
        seq = 0

        while time.perf_counter() < end_at and client.connected:
            seq += 1
            phase = (time.perf_counter() - started) * 1.7 + index * 0.31
            keys = {
                "up": math.sin(phase) > 0.55,
                "down": math.sin(phase) < -0.55,
                "left": math.cos(phase) < -0.55,
                "right": math.cos(phase) > 0.55,
            }
            await client.emit(
                "player_input",
                {
                    "seq": seq,
                    "keys": keys,
                    "aim_angle": phase % (math.pi * 2),
                    "shooting": (seq + index) % 100 < int(args.shoot_duty * 100),
                    "dash": seq % args.dash_every == 0,
                },
            )
            now = time.perf_counter()
            if now >= next_ping:
                ping_seq += 1
                ping_sent[ping_seq] = now
                await client.emit("client_ping", {"seq": ping_seq, "t": now})
                next_ping = now + 1.0
            await asyncio.sleep(args.input_interval)
    except Exception:
        metrics["errors"] += 1
    finally:
        if client.connected:
            await client.disconnect()
    return metrics


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--clients", type=int, default=100)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--ramp", type=float, default=0.02)
    parser.add_argument("--connect-timeout", type=float, default=8.0)
    parser.add_argument("--input-interval", type=float, default=0.066)
    parser.add_argument("--dash-every", type=int, default=18)
    parser.add_argument("--shoot-duty", type=float, default=0.82)
    args = parser.parse_args()

    tasks = []
    started = time.perf_counter()
    for index in range(args.clients):
        tasks.append(asyncio.create_task(run_client(index, args)))
        await asyncio.sleep(args.ramp)

    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - started
    connected = sum(1 for r in results if r["connected"])
    joined = sum(1 for r in results if r["joined"])
    errors = sum(r["errors"] for r in results)
    sync = sum(r["sync"] for r in results)
    rtts = [value for r in results for value in r["rtt"]]

    print(f"clients={args.clients} connected={connected} joined={joined} errors={errors}")
    print(f"elapsed={elapsed:.1f}s sync_packets={sync} sync_per_client={sync / max(1, joined):.1f}")
    if rtts:
        sorted_rtts = sorted(rtts)
        p95 = sorted_rtts[min(len(sorted_rtts) - 1, int(len(sorted_rtts) * 0.95))]
        print(
            "rtt_ms "
            f"avg={statistics.mean(rtts):.1f} "
            f"p50={statistics.median(rtts):.1f} "
            f"p95={p95:.1f} "
            f"max={max(rtts):.1f}"
        )
    else:
        print("rtt_ms none")


if __name__ == "__main__":
    asyncio.run(main())
