import math
import unittest

from server_game.config import (
    BLOATER_PLAYER_DAMAGE,
    BLOATER_RADIUS,
    CAMPAIGN_FINAL_WAVE,
    EXTRACTION_CAPTURE_SECONDS,
    FACILITY_SEARCH_SECONDS,
    MISSION_CAPTURE_RADIUS,
    BULLET_DAMAGE,
    DASH_DIST,
    INPUT_IDLE_TIMEOUT,
    MAZE_CELL,
    MAZE_WALL,
    MAG_SIZE,
    MOVE_ACCEL,
    MOVE_DECEL,
    PLAYER_MAX_HP,
    PLAYER_R,
    PLAYER_STALE_TIMEOUT,
    PROTOCOL_VERSION,
    RELOAD_SECONDS,
    SERVER_DT,
    MAX_RESERVE_AMMO,
    START_RESERVE_AMMO,
    VEHICLE_SPEED_MULT,
    WEAPON_TYPES,
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

    def tick_once(self, game, step=1):
        now = game._now()
        game.tick(SERVER_DT, now=now + SERVER_DT * step)

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

    def test_dash_cannot_tunnel_through_wall(self):
        game, events = self.make_game()
        game.obstacles = [{"x": 1040, "y": 920, "w": MAZE_WALL, "h": 180}]
        game._index_obstacles()

        game.handle_input("p1", {"seq": 7, "keys": {"right": True}, "dash": True})

        self.assertLessEqual(game.players["p1"]["x"], 1040 - PLAYER_R + 1)
        self.assertGreater(game.players["p1"]["x"], 1000)
        self.assertEqual([ev for ev, _ in events].count("p_dash"), 1)

    def test_shooting_input_spawns_authoritative_bullet(self):
        game, _ = self.make_game()
        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "shooting": True})
        self.tick_once(game)

        self.assertEqual(len(game.bullets), 1)
        bullet = next(iter(game.bullets.values()))
        self.assertEqual(bullet["owner"], "p1")
        self.assertGreater(bullet["vx"], 0)
        self.assertEqual(game.players["p1"]["ammo"], MAG_SIZE - 1)
        self.assertEqual(bullet["x"], bullet["spawn_x"])
        self.assertEqual(bullet["y"], bullet["spawn_y"])
        self.assertEqual(bullet["prev_x"], bullet["spawn_x"])
        self.assertEqual(bullet["prev_y"], bullet["spawn_y"])

    def test_fire_impulse_spawns_bullet_without_held_shooting(self):
        game, events = self.make_game()
        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "fire": True, "shooting": False})
        self.tick_once(game)

        self.assertEqual(len(game.bullets), 1)
        self.assertEqual(game.players["p1"]["ammo"], MAG_SIZE - 1)
        self.assertFalse(game.players["p1"]["shooting"])
        self.assertTrue(any(ev == "shot_fired" and data["ammo"] == MAG_SIZE - 1 for ev, data in events))

    def test_fire_impulse_uses_current_movement_frame_for_bullet_origin(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        start_x = player["x"]

        game.handle_input(
            "p1",
            {
                "seq": 1,
                "keys": {"right": True},
                "aim_angle": -math.pi / 2,
                "fire": True,
                "shooting": False,
            },
        )
        self.tick_once(game)

        bullet = next(iter(game.bullets.values()))
        muzzle = WEAPON_TYPES["pistol"]["muzzle"]
        self.assertGreater(player["x"], start_x)
        self.assertAlmostEqual(bullet["spawn_x"], player["x"], places=5)
        self.assertAlmostEqual(bullet["x"], player["x"], places=5)
        self.assertAlmostEqual(bullet["spawn_y"], player["y"] - muzzle, places=5)
        self.assertAlmostEqual(bullet["y"], player["y"] - muzzle, places=5)

    def test_close_zombie_attack_triggers_automatic_melee(self):
        game, events = self.make_game()
        game.zombies[1] = self.zombie(1, 1052, 1000, hp=20)

        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "fire": True})
        self.tick_once(game)

        self.assertNotIn(1, game.zombies)
        self.assertEqual(len(game.bullets), 0)
        self.assertEqual(game.players["p1"]["ammo"], MAG_SIZE)
        self.assertTrue(any(ev == "melee_swing" for ev, _ in events))
        self.assertTrue(any(ev == "z_die" and data["reason"] == "melee" for ev, data in events))

    def test_empty_weapon_still_uses_melee_when_close(self):
        game, events = self.make_game()
        player = game.players["p1"]
        player["ammo"] = 0
        player["reserve_ammo"] = 0
        game.zombies[1] = self.zombie(1, 1052, 1000, hp=20)

        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "fire": True})
        self.tick_once(game)

        self.assertNotIn(1, game.zombies)
        self.assertEqual(len(game.bullets), 0)
        self.assertEqual(player["ammo"], 0)
        self.assertTrue(any(ev == "melee_swing" for ev, _ in events))

    def test_inventory_pause_freezes_and_protects_player(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["protect_until"] = 0
        player["shield_until"] = 0
        game.zombies[1] = self.zombie(1, 1040, 1000, hp=60)

        game.handle_input("p1", {
            "seq": 1,
            "keys": {"right": True},
            "shooting": True,
            "fire": True,
            "paused": True,
        })
        for i in range(8):
            game.tick(SERVER_DT, now=now + (i + 1) * SERVER_DT)

        self.assertTrue(player["paused"])
        self.assertEqual(player["x"], 1000)
        self.assertEqual(player["hp"], PLAYER_MAX_HP)
        self.assertFalse(player["shooting"])
        self.assertEqual(len(game.bullets), 0)
        self.assertFalse(any(ev == "shot_fired" for ev, _ in events))

    def test_inventory_pause_does_not_charge_extraction(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        exit_point = {
            "id": "pause-exit",
            "type": "service",
            "name": "维修通道",
            "text": "撤离",
            "requires": {},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#66d9ff",
        }
        game.extractions = [exit_point]
        player["paused"] = True

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, game._now())

        self.assertEqual(exit_point["charge"], 0)

    def test_ammo_is_finite_and_reload_uses_reserve(self):
        game, events = self.make_game()
        player = game.players["p1"]
        player["ammo"] = 1
        player["reserve_ammo"] = 12

        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "shooting": True})
        self.tick_once(game)
        self.assertEqual(player["ammo"], 0)
        game.handle_input("p1", {"seq": 2, "reload": True})
        self.assertGreater(player["reload_until"], 0)
        game.tick(SERVER_DT, now=player["reload_until"] + RELOAD_SECONDS)

        self.assertEqual(player["ammo"], 12)
        self.assertEqual(player["reserve_ammo"], 0)
        self.assertTrue(any(ev == "reload_start" for ev, _ in events))
        self.assertTrue(any(ev == "reload_done" for ev, _ in events))

    def test_weapon_switch_to_rifle_uses_rifle_stats(self):
        game, events = self.make_game()
        player = game.players["p1"]
        now = game._now()
        game._unlock_weapon(player, "rifle", now, notify=False)

        game.handle_input("p1", {"seq": 1, "weapon": "rifle", "aim_angle": 0, "fire": True})
        self.tick_once(game)

        self.assertEqual(player["weapon_id"], "rifle")
        bullet = next(iter(game.bullets.values()))
        self.assertEqual(bullet["weapon"], "rifle")
        self.assertEqual(bullet["damage"], WEAPON_TYPES["rifle"]["damage"])
        self.assertEqual(bullet["pierce"], WEAPON_TYPES["rifle"]["pierce"])
        self.assertGreater(bullet["vx"], WEAPON_TYPES["pistol"]["bullet_speed"])
        self.assertTrue(any(ev == "weapon_switch" for ev, _ in events))

    def test_shotgun_fires_multiple_pellets(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        now = game._now()
        game._unlock_weapon(player, "shotgun", now, notify=False)

        game.handle_input("p1", {"seq": 1, "weapon": "shotgun", "aim_angle": 0, "fire": True})
        self.tick_once(game)

        self.assertEqual(player["weapon_id"], "shotgun")
        self.assertEqual(len(game.bullets), WEAPON_TYPES["shotgun"]["pellets"])
        self.assertTrue(all(bullet["weapon"] == "shotgun" for bullet in game.bullets.values()))

    def test_projectiles_spawn_from_base_muzzle_when_firing_up(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        now = game._now()
        game._unlock_weapon(player, "shotgun", now, notify=False)

        game.handle_input("p1", {"seq": 1, "weapon": "shotgun", "aim_angle": -math.pi / 2, "fire": True})
        self.tick_once(game)

        muzzle = WEAPON_TYPES["shotgun"]["muzzle"]
        self.assertEqual(len(game.bullets), WEAPON_TYPES["shotgun"]["pellets"])
        for bullet in game.bullets.values():
            self.assertAlmostEqual(bullet["x"], player["x"], places=5)
            self.assertAlmostEqual(bullet["y"], player["y"] - muzzle, places=5)
            self.assertAlmostEqual(bullet["spawn_x"], player["x"], places=5)
            self.assertAlmostEqual(bullet["spawn_y"], player["y"] - muzzle, places=5)

    def test_launcher_explosion_damages_group(self):
        game, events = self.make_game()
        now = game._now()
        game.zombies[1] = self.zombie(1, 1030, 1000, hp=30)
        game.zombies[2] = self.zombie(2, 1120, 1000, hp=30)
        game.zombies[3] = self.zombie(3, 1380, 1000, hp=30)

        game._explode_projectile({
            "owner": "p1",
            "x": 1000,
            "y": 1000,
            "damage": 34,
            "explosion_radius": WEAPON_TYPES["launcher"]["explosion_radius"],
            "explosion_damage": WEAPON_TYPES["launcher"]["explosion_damage"],
            "color": "#ff8844",
        }, now)

        self.assertNotIn(1, game.zombies)
        self.assertNotIn(2, game.zombies)
        self.assertIn(3, game.zombies)
        self.assertTrue(any(ev == "grenade_explode" for ev, _ in events))

    def test_facility_rooms_apply_gameplay_effects(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        room = {
            "kind": "room", "id": "medbay-test", "effect": "medbay", "label": "病房",
            "x": 930, "y": 930, "w": 180, "h": 160, "active": True, "searched": False,
        }
        game.map_features = [room]
        player["hp"] = 52

        game._apply_facility_effects(1.0, now)

        self.assertGreater(player["hp"], 52)
        self.assertEqual(player["facility_label"], "病房")
        self.assertIn("止血", player["facility_status"])
        self.assertTrue(any(ev == "fog_wave" and data["reason"] == "medbay" for ev, data in events))

    def test_generator_consumes_fuse_and_reveals_exit(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        game.map_features = [{
            "kind": "room", "id": "generator-test", "effect": "generator", "label": "机房",
            "x": 930, "y": 930, "w": 180, "h": 160, "active": True, "searched": False,
        }]
        exit_point = game.extractions[0]
        exit_point["visible"] = False
        game.extractions = [exit_point]
        game.task_counts = {"fuse": 1, "sample": 0, "keycard": 0}

        game._apply_facility_effects(SERVER_DT, now)

        self.assertEqual(game.task_counts["fuse"], 0)
        self.assertTrue(game.extractions[0]["visible"])
        self.assertTrue(any(ev == "mission_revealed" for ev, _ in events))
        self.assertTrue(any(ev == "facility_used" for ev, _ in events))
        self.assertTrue(any(ev == "fog_wave" and data["reason"] == "generator" for ev, data in events))

    def test_lab_entry_triggers_fog_pressure(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        room = {
            "kind": "room", "id": "lab-test", "effect": "lab", "label": "样本库",
            "x": 930, "y": 930, "w": 180, "h": 160, "active": True, "searched": False,
        }
        game.map_features = [room]

        game._apply_facility_effects(SERVER_DT, now)
        game._apply_facility_effects(SERVER_DT, now + SERVER_DT)

        self.assertEqual(player["facility_label"], "样本库")
        self.assertGreater(game.lab_sample_until, now)
        self.assertTrue(room["alarm_spawned"])
        self.assertIn("样本共振", player["facility_status"])
        self.assertTrue(any(ev == "lab_reactor" for ev, _ in events))
        self.assertTrue(any(ev == "fog_wave" and data["reason"] == "lab" for ev, data in events))

    def test_armory_search_spawns_weapon_reward(self):
        game, events = self.make_game()
        now = game._now()
        game.items.clear()
        room = {
            "kind": "room", "id": "armory-test", "effect": "armory", "label": "仓库",
            "x": 930, "y": 930, "w": 180, "h": 160, "active": True, "searched": False,
        }
        game.map_features = [room]

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS + 0.05, now)

        self.assertTrue(any(item["type"].startswith("weapon_") for item in game.items.values()))
        self.assertTrue(any(ev == "facility_used" for ev, _ in events))
        item_count = len(game.items)

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS + 0.05, now + 1)

        self.assertTrue(room["searched"])
        self.assertEqual(len(game.items), item_count)

    def test_vehicle_pickup_enables_ram_damage(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        item = {
            "id": 9, "x": player["x"], "y": player["y"], "type": "vehicle",
            "color": "#ffc247", "icon": "V", "name": "维修推车", "radius": 15,
        }
        game._apply_item("p1", item, now)
        game.zombies[1] = self.zombie(1, 1034, 1000, hp=70)
        player["keys"] = {"right": True}

        for i in range(8):
            game._update_players(SERVER_DT, now + (i + 1) * SERVER_DT)

        self.assertTrue(now < player["vehicle_until"])
        self.assertGreater(player["vx"], player_speed() * 0.8)
        self.assertLess(game.zombies.get(1, {"hp": 0})["hp"], 70)
        self.assertTrue(any(ev == "vehicle_hit" for ev, _ in events))

    def test_snapshot_has_version_tick_ack_and_perf(self):
        game, _ = self.make_game()
        game.handle_input("p1", {"seq": 3, "keys": {}})
        snap = game.get_snapshot()

        self.assertEqual(snap["v"], PROTOCOL_VERSION)
        self.assertIn("tick", snap)
        self.assertIn("time", snap)
        self.assertEqual(snap["p"]["p1"][14], 3)
        self.assertEqual(len(snap["p"]["p1"]), 36)
        self.assertIn("perf", snap)
        self.assertIn("tick_ms", snap["perf"])
        self.assertIn("lb", snap)
        self.assertIn("obj", snap)
        self.assertIn("remaining", snap["obj"])
        self.assertNotIn("base", snap)
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
        self.assertNotIn("base", init)
        self.assertIn("mission", init)
        self.assertIn("exits", init)
        self.assertIn("weaponTypes", init["cfg"])
        self.assertIn("vehicleSpeedMult", init["cfg"])
        self.assertEqual(init["cfg"]["weaponTypes"]["pistol"]["mag_size"], MAG_SIZE)
        self.assertEqual(game.players["p1"]["ammo"], MAG_SIZE)
        self.assertEqual(game.players["p1"]["reserve_ammo"], START_RESERVE_AMMO)

    def test_facility_layout_is_not_fixed_square_maze(self):
        game = Game()

        self.assertNotEqual(game.maze_cols, game.maze_rows)
        self.assertGreater(len(game.floor_points), 35)
        self.assertGreater(len(game.map_features), 3)
        self.assertTrue(any(feature.get("kind") == "room" for feature in game.map_features))
        self.assertTrue(any(exit_point.get("rewardTitle") for exit_point in game.extractions))

        game.add_player("p1")
        init = game.get_init_data("p1", game.players["p1"]["idx"])
        self.assertIn("features", init)
        self.assertGreater(len(init["features"]), 3)
        self.assertIn("stage", init)
        self.assertIn("stageTitle", init["obj"])

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

    def test_item_pickup_matches_visual_overlap(self):
        game, events = self.make_game()
        now = game._now()
        game.items[1] = {
            "id": 1, "x": 1048, "y": 1000, "type": "parts",
            "color": "#ffc247", "icon": "P", "name": "零件", "radius": 15,
        }

        game.tick(SERVER_DT, now=now)

        self.assertNotIn(1, game.items)
        self.assertGreater(game.players["p1"]["materials"], 0)
        self.assertTrue(any(ev == "item_pick" and data["type"] == "parts" for ev, data in events))

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
        game.maze_openings = {}
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

    def test_zombie_uses_maze_route_around_closed_wall(self):
        game, _ = self.make_game()
        now = game._now()
        game.maze_margin = (0, 0)
        game.maze_openings = {
            (0, 0): {"S"},
            (0, 1): {"N", "E"},
            (1, 1): {"W", "N"},
            (1, 0): {"S"},
        }
        wall_x = MAZE_CELL - MAZE_WALL / 2
        game.obstacles = [{"x": wall_x, "y": -MAZE_WALL / 2, "w": MAZE_WALL, "h": MAZE_CELL + MAZE_WALL}]
        game._index_obstacles()
        game.players["p1"]["x"] = MAZE_CELL * 1.5
        game.players["p1"]["y"] = MAZE_CELL * 0.5
        game.zombies[1] = self.zombie(1, MAZE_CELL * 0.5, MAZE_CELL * 0.5, hp=90)

        for i in range(70):
            game.tick(SERVER_DT, now=now + i * SERVER_DT)

        zombie = game.zombies[1]
        self.assertGreater(zombie["y"], MAZE_CELL * 0.72)
        self.assertLess(zombie["x"], wall_x - zombie["radius"])

    def test_zombie_targets_player_without_base_objective(self):
        game, events = self.make_game()
        now = game._now()
        game.players["p1"]["x"] = 1120
        game.players["p1"]["y"] = 1000
        game.zombies[1] = self.zombie(1, 900, 1000, hp=90)

        for i in range(8):
            game.tick(SERVER_DT, now=now + i * SERVER_DT)

        self.assertEqual(game.zombies[1]["target"], "p1")
        self.assertGreater(math.hypot(game.zombies[1]["x"] - 900, game.zombies[1]["y"] - 1000), 0.5)
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

        self.assertEqual(game.wave, old_wave)
        self.assertIsNotNone(game.intermission)
        self.assertGreater(player["score"], 0)
        self.assertTrue(any(ev == "mission_complete" for ev, _ in events))
        self.assertTrue(any(ev == "intermission_start" for ev, _ in events))
        self.assertFalse(any(ev == "wave_start" for ev, _ in events))

        game.continue_intermission("p1")

        self.assertEqual(game.wave, old_wave + 1)
        self.assertIsNone(game.intermission)
        self.assertGreater(len(game.obstacles), 20)
        self.assertGreaterEqual(len(game.extractions), 3)
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_multiplayer_intermission_waits_for_all_live_players(self):
        game, events = self.make_game()
        now = game._now()
        game.add_player("p2")
        player = game.players["p1"]
        exit_point = {
            "id": "team-exit",
            "type": "service",
            "name": "维修通道",
            "text": "整队撤离",
            "requires": {},
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
        old_wave = game.wave

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)
        game.continue_intermission("p1")

        self.assertEqual(game.wave, old_wave)
        self.assertIsNotNone(game.intermission)
        self.assertEqual(set(game.intermission["players"]), {"p1", "p2"})
        self.assertEqual(game.intermission["ready"], ["p1"])
        self.assertFalse(any(ev == "wave_start" for ev, _ in events))

        game.continue_intermission("p2")

        self.assertEqual(game.wave, old_wave + 1)
        self.assertIsNone(game.intermission)
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_disconnect_during_intermission_scrubs_waiting_player(self):
        game, events = self.make_game()
        now = game._now()
        game.add_player("p2")
        player = game.players["p1"]
        exit_point = {
            "id": "disconnect-exit",
            "type": "service",
            "name": "维修通道",
            "text": "断线撤离",
            "requires": {},
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
        old_wave = game.wave

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)
        game.continue_intermission("p1")
        game.remove_player("p2")

        self.assertEqual(game.wave, old_wave + 1)
        self.assertIsNone(game.intermission)
        self.assertNotIn("p2", game.players)
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_service_extraction_grants_route_reward_for_next_stage(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["reserve_ammo"] = 10
        exit_point = {
            "id": "service-reward",
            "type": "service",
            "name": "维修通道",
            "text": "找到保险丝，恢复卷帘门供电",
            "requires": {},
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

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)

        self.assertGreater(player["reserve_ammo"], 10)
        self.assertLessEqual(player["reserve_ammo"], MAX_RESERVE_AMMO)
        complete = [data for ev, data in events if ev == "mission_complete"][-1]
        self.assertEqual(complete["rewardTitle"], "弹药缓存")
        self.assertIsNotNone(game.intermission)

        game.continue_intermission("p1")

        started = [data for ev, data in events if ev == "wave_start"][-1]
        self.assertEqual(started["routeReward"]["route"], "service")
        self.assertIn("features", started)

    def test_intermission_talent_purchase_spends_parts_and_applies_effect(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["materials"] = 6
        exit_point = {
            "id": "talent-exit",
            "type": "service",
            "name": "维修通道",
            "text": "测试整备",
            "requires": {},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.99,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#d98cff",
        }
        game.extractions = [exit_point]
        game.mission = exit_point

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)
        bought = game.buy_talent("p1", "vitality")

        self.assertTrue(bought)
        self.assertEqual(player["talents"]["vitality"], 1)
        self.assertEqual(player["materials"], 4)
        self.assertEqual(player["max_hp"], PLAYER_MAX_HP + 12)
        self.assertTrue(any(ev == "talent_upgrade" for ev, _ in events))
        upgraded = [data for ev, data in events if ev == "talent_upgrade"][-1]
        self.assertEqual(upgraded["intermission"]["talents"]["vitality"]["level"], 1)

        game.continue_intermission("p1")

        self.assertIsNone(game.intermission)
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_intermission_previews_next_boss_wave(self):
        game, events = self.make_game()
        now = game._now()
        game.wave = 2
        player = game.players["p1"]
        exit_point = {
            "id": "boss-preview",
            "type": "security",
            "name": "安保电梯",
            "text": "测试 Boss 预告",
            "requires": {},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.99,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#d98cff",
        }
        game.extractions = [exit_point]
        game.mission = exit_point

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)

        intermissions = [data for ev, data in events if ev == "intermission_start"]
        self.assertTrue(intermissions)
        self.assertTrue(intermissions[-1]["nextBoss"])
        self.assertEqual(intermissions[-1]["bossName"], "黑墙巨像")

    def test_final_wave_opens_story_ending_before_endless(self):
        game, events = self.make_game()
        now = game._now()
        game.wave = CAMPAIGN_FINAL_WAVE
        player = game.players["p1"]
        exit_point = {
            "id": "final-exit",
            "type": "security",
            "name": "安保电梯",
            "text": "最终撤离",
            "requires": {},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.99,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#d98cff",
        }
        game.extractions = [exit_point]
        game.mission = exit_point

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)

        complete = [data for ev, data in events if ev == "mission_complete"][-1]
        intermission = [data for ev, data in events if ev == "intermission_start"][-1]
        self.assertTrue(complete["ending"])
        self.assertTrue(intermission["ending"])
        self.assertIn("B13", intermission["endingTitle"])

        game.continue_intermission("p1")

        self.assertEqual(game.wave, CAMPAIGN_FINAL_WAVE + 1)

    def test_lab_route_reveals_one_exit_on_next_stage(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        exit_point = {
            "id": "lab-reward",
            "type": "lab",
            "name": "净化闸门",
            "text": "击杀感染体取得样本，骗过净化扫描",
            "requires": {},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.99,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#b7ff47",
        }
        game.extractions = [exit_point]
        game.mission = exit_point

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)

        complete = [data for ev, data in events if ev == "mission_complete"][-1]
        self.assertEqual(complete["rewardTitle"], "净化情报")
        self.assertIsNotNone(game.intermission)

        game.continue_intermission("p1")

        self.assertTrue(any(exit_point.get("visible") for exit_point in game.extractions))
        started = [data for ev, data in events if ev == "wave_start"][-1]
        self.assertEqual(started["routeReward"]["route"], "lab")

    def test_visible_exit_announces_when_requirements_are_met(self):
        game, events = self.make_game()
        player = game.players["p1"]
        exit_point = {
            "id": "service-ready",
            "type": "service",
            "name": "维修通道",
            "text": "找到保险丝，恢复卷帘门供电",
            "requires": {"fuse": 1},
            "x": player["x"] + 300,
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0,
            "visible": True,
            "done": False,
            "ready_notified": False,
            "wave": game.wave,
            "color": "#66d9ff",
        }
        game.extractions = [exit_point]
        game.task_counts = {"fuse": 0, "sample": 0, "keycard": 0}

        game._update_mission(SERVER_DT, game._now())
        game.task_counts["fuse"] = 1
        game._update_mission(SERVER_DT, game._now() + SERVER_DT)
        game._update_mission(SERVER_DT, game._now() + SERVER_DT * 2)

        ready_events = [data for ev, data in events if ev == "exit_ready"]
        self.assertEqual(len(ready_events), 1)
        self.assertEqual(ready_events[0]["id"], "service-ready")

    def test_starting_extraction_triggers_fog_wave(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        exit_point = {
            "id": "service-charge",
            "type": "service",
            "name": "维修通道",
            "text": "撤离测试",
            "requires": {},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#66d9ff",
        }
        game.extractions = [exit_point]
        game.mission = exit_point

        game._update_mission(SERVER_DT, now)

        self.assertGreater(exit_point["charge"], 0)
        self.assertTrue(exit_point["charge_fog_spawned"])
        fog_events = [data for ev, data in events if ev == "fog_wave" and data["reason"] == "extraction"]
        self.assertTrue(fog_events)
        self.assertEqual(fog_events[-1]["scene"], "撤离封锁")
        self.assertEqual(fog_events[-1]["col"], "#ff4d5f")
        self.assertAlmostEqual(fog_events[-1]["x"], exit_point["x"], delta=0.1)

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
        game.wave = 3
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

    def test_first_wave_burst_introduces_mixed_infected(self):
        game, _ = self.make_game()
        game.wave = 1
        game.wave_remaining = 80
        game.zombies.clear()

        game._spawn_wave_burst()

        types = {zombie["type"] for zombie in game.zombies.values()}
        self.assertTrue({"runner", "crawler", "brute", "toxic"}.issubset(types))

    def test_fog_wave_refills_empty_pressure(self):
        game, events = self.make_game()
        now = game._now()
        game.wave = 1
        game.wave_remaining = 80
        game.zombies.clear()

        game._director_pressure(2.0, now)

        types = {zombie["type"] for zombie in game.zombies.values()}
        self.assertIn("shade", types)
        self.assertTrue(any(ev == "fog_wave" for ev, _ in events))

    def test_fog_wave_uses_infection_source_after_wave_budget_is_empty(self):
        game, events = self.make_game()
        now = game._now()
        game.wave_remaining = 0
        game.infection_source_remaining = 12
        game.zombies.clear()

        spawned = game._trigger_fog_wave(now, reason="silence", force=True)

        self.assertGreater(spawned, 0)
        self.assertEqual(game.wave_remaining, 0)
        self.assertLess(game.infection_source_remaining, 12)
        source_events = [data for ev, data in events if ev == "fog_wave"]
        self.assertTrue(source_events)
        self.assertGreater(source_events[-1]["sourceCount"], 0)
        self.assertTrue(any(zombie.get("source") == "infection" for zombie in game.zombies.values()))

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
