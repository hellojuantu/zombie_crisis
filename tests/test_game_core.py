import unittest

from server_game.config import (
    BLOATER_PLAYER_DAMAGE,
    BLOATER_RADIUS,
    EXTRACTION_CAPTURE_SECONDS,
    MISSION_CAPTURE_RADIUS,
    BULLET_DAMAGE,
    DASH_DIST,
    INPUT_IDLE_TIMEOUT,
    MOVE_ACCEL,
    MOVE_DECEL,
    PLAYER_MAX_HP,
    PLAYER_STALE_TIMEOUT,
    PROTOCOL_VERSION,
    SERVER_DT,
    ZOMBIE_TYPES,
)
from server_game.simulation import (
    Game,
    player_speed,
)


class GameCoreTest(unittest.TestCase):
    def make_game(self):
        events = []
        game = Game(emitter=lambda ev, data: events.append((ev, data)))
        game.obstacles = []
        game.obstacle_grid = {}
        game.zombies.clear()
        game.bullets.clear()
        game.items.clear()
        game.wave_remaining = 999
        game.zombie_spawn_timer = -999
        game.item_spawn_timer = -999
        game.add_player("p1")
        game.running = True
        player = game.players["p1"]
        player["x"] = 1000
        player["y"] = 1000
        player["protect_until"] = 0
        player["shield_until"] = 0
        return game, events

    def zombie(self, zid, x, y, hp=20, ztype="walker"):
        meta = ZOMBIE_TYPES.get(ztype, ZOMBIE_TYPES["walker"])
        return {
            "id": zid, "x": x, "y": y, "vx": 0, "vy": 0,
            "type": ztype, "hp": hp, "max_hp": hp, "radius": meta["radius"],
            "color": meta["color"], "target": None, "leap_cd": 0,
            "scream_cd": 0, "rally_until": 0,
        }

    def test_movement_uses_fixed_seconds_not_input_count(self):
        game, _ = self.make_game()
        start = game._now()
        speed = player_speed()
        game.handle_input("p1", {"seq": 1, "keys": {"right": True}})
        game.players["p1"]["last_input"] = start
        game.players["p1"]["last_seen"] = start

        for i in range(30):
            now = start + (i + 1) * SERVER_DT
            if i % 3 == 0:
                game.players["p1"]["last_input"] = now
                game.players["p1"]["last_seen"] = now
            game.tick(SERVER_DT, now=now)

        self.assertGreater(game.players["p1"]["x"], 1000 + speed * 0.82)
        self.assertLess(game.players["p1"]["x"], 1000 + speed)
        self.assertAlmostEqual(game.players["p1"]["vx"], speed, delta=0.1)

    def test_old_input_sequence_is_ignored(self):
        game, _ = self.make_game()
        game.handle_input("p1", {"seq": 2, "keys": {"right": True}})
        game.handle_input("p1", {"seq": 1, "keys": {"left": True}})

        self.assertTrue(game.players["p1"]["keys"]["right"])
        self.assertFalse(game.players["p1"]["keys"].get("left", False))
        self.assertEqual(game.players["p1"]["ack_seq"], 2)

    def test_input_timeout_stops_sticky_movement_and_shooting(self):
        game, _ = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["keys"] = {"right": True}
        player["shooting"] = True
        player["last_input"] = now - INPUT_IDLE_TIMEOUT - 0.1
        player["last_seen"] = now
        game.tick(SERVER_DT, now=now)

        self.assertEqual(player["keys"], {})
        self.assertFalse(player["shooting"])
        self.assertEqual(player["vx"], 0)
        self.assertEqual(player["vy"], 0)
        self.assertAlmostEqual(player["x"], 1000, delta=0.1)

    def test_stale_player_is_removed(self):
        game, events = self.make_game()
        now = game._now()
        game.players["p1"]["last_seen"] = now - PLAYER_STALE_TIMEOUT - 0.1
        game.tick(SERVER_DT, now=now)

        self.assertNotIn("p1", game.players)
        self.assertIn(("p_leave", {"pid": "p1", "reason": "timeout"}), events)

    def test_ping_seen_keeps_idle_player_connected(self):
        game, _ = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["last_input"] = now - INPUT_IDLE_TIMEOUT - 0.1
        player["last_seen"] = now - PLAYER_STALE_TIMEOUT - 0.1

        game.mark_seen("p1", now=now)
        game.tick(SERVER_DT, now=now)

        self.assertIn("p1", game.players)
        self.assertEqual(player["keys"], {})

    def test_dash_is_distance_limited_and_acknowledged(self):
        game, events = self.make_game()
        game.handle_input("p1", {"seq": 7, "keys": {"right": True}, "dash": True})

        self.assertAlmostEqual(game.players["p1"]["x"], 1000 + DASH_DIST, delta=0.1)
        self.assertEqual(game.players["p1"]["ack_seq"], 7)
        self.assertEqual([ev for ev, _ in events].count("p_dash"), 1)

    def test_shooting_input_spawns_authoritative_bullet(self):
        game, _ = self.make_game()
        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "shooting": True})

        self.assertEqual(len(game.bullets), 1)
        bullet = next(iter(game.bullets.values()))
        self.assertEqual(bullet["owner"], "p1")
        self.assertGreater(bullet["vx"], 0)

    def test_snapshot_has_version_tick_ack_and_perf(self):
        game, _ = self.make_game()
        game.handle_input("p1", {"seq": 3, "keys": {}})
        snap = game.get_snapshot()

        self.assertEqual(snap["v"], PROTOCOL_VERSION)
        self.assertIn("tick", snap)
        self.assertIn("time", snap)
        self.assertEqual(snap["p"]["p1"][14], 3)
        self.assertEqual(len(snap["p"]["p1"]), 22)
        self.assertIn("perf", snap)
        self.assertIn("tick_ms", snap["perf"])
        self.assertIn("lb", snap)
        self.assertIn("obj", snap)
        self.assertIn("remaining", snap["obj"])
        self.assertIn("base", snap)
        self.assertIsNone(snap["base"])
        self.assertIn("mission", snap)
        self.assertIn("exits", snap)
        self.assertGreaterEqual(len(snap["exits"]), 3)

    def test_snapshot_filters_zombies_by_player_interest(self):
        game, _ = self.make_game()
        game.zombies[1] = self.zombie(1, 1040, 1000)
        game.zombies[2] = self.zombie(2, 3300, 3300)

        snap = game.get_snapshot("p1")

        self.assertIn(1, snap["z"])
        self.assertNotIn(2, snap["z"])
        self.assertEqual(snap["zt"], 2)

    def test_init_data_exposes_authoritative_tuning(self):
        game, _ = self.make_game()
        init = game.get_init_data("p1", game.players["p1"]["idx"])

        self.assertEqual(init["cfg"]["playerSpeed"], 315)
        self.assertEqual(init["cfg"]["dashDist"], DASH_DIST)
        self.assertEqual(init["cfg"]["moveAccel"], MOVE_ACCEL)
        self.assertEqual(init["cfg"]["moveDecel"], MOVE_DECEL)
        self.assertEqual(init["cfg"]["playerMaxHp"], PLAYER_MAX_HP)
        self.assertIn("z", init)
        self.assertIn("b", init)
        self.assertIn("i", init)
        self.assertIn("lb", init)
        self.assertIn("obj", init)
        self.assertIn("story", init["obj"])
        self.assertIn("base", init)
        self.assertIsNone(init["base"])
        self.assertIn("mission", init)
        self.assertIn("exits", init)

    def test_bullet_damages_and_kills_zombie(self):
        game, events = self.make_game()
        now = game._now()
        game.zombies[1] = self.zombie(1, 1052, 1000, hp=BULLET_DAMAGE)

        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "shooting": True})
        game.tick(SERVER_DT, now=now + SERVER_DT)

        self.assertNotIn(1, game.zombies)
        self.assertGreater(game.players["p1"]["score"], 0)
        self.assertTrue(any(ev == "z_die" for ev, _ in events))
        self.assertTrue(any(ev == "score_gain" for ev, _ in events))

    def test_items_apply_rapid_fire_effect(self):
        game, events = self.make_game()
        now = game._now()
        game.items[1] = {
            "id": 1, "x": 1000, "y": 1000, "type": "rapid",
            "color": "#44ffaa", "icon": "R", "name": "速射", "radius": 15,
        }

        game.tick(SERVER_DT, now=now)

        self.assertNotIn(1, game.items)
        self.assertGreater(game.players["p1"]["rapid_until"], now)
        self.assertTrue(any(ev == "item_pick" and data["type"] == "rapid" for ev, data in events))

    def test_task_item_updates_stage_collection_state(self):
        game, events = self.make_game()
        now = game._now()
        game.task_counts = {"fuse": 0, "sample": 0, "keycard": 0}
        game.items[1] = {
            "id": 1, "x": 1000, "y": 1000, "type": "fuse",
            "color": "#66d9ff", "icon": "F", "name": "保险丝", "radius": 15,
        }

        game.tick(SERVER_DT, now=now)

        self.assertEqual(game.task_counts["fuse"], 1)
        self.assertTrue(any(ev == "task_update" and data["type"] == "fuse" for ev, data in events))
        self.assertTrue(any(ev == "item_pick" and data["type"] == "fuse" for ev, data in events))

    def test_zombie_contact_damages_player(self):
        game, _ = self.make_game()
        now = game._now()
        game.zombies[1] = self.zombie(1, 1010, 1000, hp=40)

        game.tick(SERVER_DT, now=now)

        self.assertLess(game.players["p1"]["hp"], PLAYER_MAX_HP)

    def test_zombie_steers_around_obstacle_instead_of_stalling(self):
        game, _ = self.make_game()
        now = game._now()
        game.obstacles = [{"x": 940, "y": 930, "w": 95, "h": 140}]
        game._index_obstacles()
        game.zombies[1] = self.zombie(1, 920, 1000, hp=90)
        game.players["p1"]["x"] = 1120
        game.players["p1"]["y"] = 1000

        for i in range(50):
            game.tick(SERVER_DT, now=now + i * SERVER_DT)

        zombie = game.zombies[1]
        self.assertGreater(abs(zombie["y"] - 1000), 10)
        self.assertGreater(zombie["x"], 920)

    def test_zombie_targets_player_without_base_objective(self):
        game, events = self.make_game()
        now = game._now()
        game.players["p1"]["x"] = 1120
        game.players["p1"]["y"] = 1000
        game.zombies[1] = self.zombie(1, 900, 1000, hp=90)

        for i in range(8):
            game.tick(SERVER_DT, now=now + i * SERVER_DT)

        self.assertEqual(game.zombies[1]["target"], "p1")
        self.assertGreater(game.zombies[1]["x"], 900)
        self.assertFalse(any(ev.startswith("base_") for ev, _ in events))

    def test_conditioned_extraction_advances_to_next_maze_stage(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        exit_point = {
            "id": "service-test",
            "type": "service",
            "name": "维修通道",
            "text": "找到保险丝，恢复卷帘门供电",
            "requires": {"fuse": 2},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.99,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#66d9ff",
        }
        game.extractions = [exit_point]
        game.mission = exit_point
        game.task_counts = {"fuse": 2, "sample": 0, "keycard": 0}
        old_wave = game.wave

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)

        self.assertEqual(game.wave, old_wave + 1)
        self.assertIsNone(game.base)
        self.assertGreater(len(game.obstacles), 20)
        self.assertGreaterEqual(len(game.extractions), 3)
        self.assertGreater(player["score"], 0)
        self.assertTrue(any(ev == "mission_complete" for ev, _ in events))
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_nuke_item_clears_nearby_zombies(self):
        game, events = self.make_game()
        now = game._now()
        game.zombies[1] = self.zombie(1, 1040, 1000, hp=40)
        game.zombies[2] = self.zombie(2, 1700, 1000, hp=40)
        game.items[1] = {
            "id": 1, "x": 1000, "y": 1000, "type": "nuke",
            "color": "#ff8844", "icon": "!", "name": "清场炸弹", "radius": 15,
        }

        game.tick(SERVER_DT, now=now)

        self.assertNotIn(1, game.zombies)
        self.assertIn(2, game.zombies)
        self.assertTrue(any(ev == "nuke" for ev, _ in events))

    def test_clearing_zombies_does_not_advance_without_extraction(self):
        game, events = self.make_game()
        now = game._now()
        game.wave = 1
        game.wave_remaining = 0
        game.zombies.clear()

        game.tick(SERVER_DT, now=now)

        self.assertEqual(game.wave, 1)
        self.assertFalse(any(ev == "wave_start" for ev, _ in events))

    def test_combo_bonus_grants_temporary_rapid_fire(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["combo"] = 9
        player["combo_until"] = now + 2

        game._gain_score("p1", 12, 8, now)

        self.assertEqual(player["combo"], 10)
        self.assertGreater(player["rapid_until"], now)
        self.assertTrue(any(ev == "combo_bonus" and data["type"] == "rapid" for ev, data in events))

    def test_boss_wave_burst_spawns_and_announces_boss(self):
        game, events = self.make_game()
        game.wave = 5
        game.wave_remaining = 50
        game.zombies.clear()

        game._spawn_wave_burst()

        self.assertTrue(any(zombie["type"] == "boss" for zombie in game.zombies.values()))
        self.assertTrue(any(ev == "boss_spawn" for ev, _ in events))

    def test_wave_burst_introduces_advanced_zombie_roles(self):
        game, _ = self.make_game()
        game.wave = 7
        game.wave_remaining = 80
        game.zombies.clear()

        game._spawn_wave_burst()

        types = {zombie["type"] for zombie in game.zombies.values()}
        self.assertTrue({"crawler", "armored", "leaper", "screamer", "bloater"}.issubset(types))

    def test_leaper_uses_burst_movement_and_emits_warning(self):
        game, events = self.make_game()
        now = game._now()
        game.zombies[1] = self.zombie(1, 520, 1000, hp=80, ztype="leaper")

        game.tick(SERVER_DT, now=now)

        zombie = game.zombies[1]
        self.assertGreater((zombie["vx"] ** 2 + zombie["vy"] ** 2) ** 0.5, ZOMBIE_TYPES["leaper"]["speed"] * 2)
        self.assertGreater(zombie["leap_cd"], now)
        self.assertTrue(any(ev == "z_leap" for ev, _ in events))

    def test_screamer_rallies_nearby_zombies(self):
        game, events = self.make_game()
        now = game._now()
        game.zombies[1] = self.zombie(1, 900, 1000, hp=80, ztype="screamer")
        game.zombies[2] = self.zombie(2, 940, 1000, hp=80, ztype="walker")

        game.tick(SERVER_DT, now=now)

        self.assertGreater(game.zombies[2]["rally_until"], now)
        self.assertTrue(any(ev == "z_scream" and data["buffed"] >= 1 for ev, data in events))

    def test_bloater_explosion_damages_nearby_entities(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["protect_until"] = 0
        player["shield_until"] = 0
        player["x"] = 1000
        player["y"] = 1000
        game.zombies[1] = self.zombie(1, 1010, 1000, hp=10, ztype="bloater")
        game.zombies[2] = self.zombie(2, 1010 + BLOATER_RADIUS - 20, 1000, hp=80, ztype="walker")

        game._kill_zombie("p1", 1, game.zombies[1], now)

        self.assertEqual(player["hp"], PLAYER_MAX_HP - BLOATER_PLAYER_DAMAGE)
        self.assertLess(game.zombies[2]["hp"], 80)
        self.assertTrue(any(ev == "z_explode" for ev, _ in events))

    def test_director_repositions_far_zombie_back_into_pressure(self):
        game, _ = self.make_game()
        now = game._now()
        game.wave_remaining = 0
        game.zombies[1] = self.zombie(1, 3300, 3300, hp=40)
        game.zombies[1]["far_since"] = now - 10

        game._director_pressure(2.0, now)

        zombie = game.zombies[1]
        distance = ((zombie["x"] - 1000) ** 2 + (zombie["y"] - 1000) ** 2) ** 0.5
        self.assertLess(distance, 980)
        self.assertEqual(zombie.get("far_since"), 0)


if __name__ == "__main__":
    unittest.main()
