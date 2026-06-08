import math
import unittest

import server_game.simulation as simulation_module
from server_game.config import (
    BLOATER_PLAYER_DAMAGE,
    BLOATER_RADIUS,
    CAMPAIGN_FINAL_WAVE,
    EXTRACTION_CAPTURE_SECONDS,
    FACILITY_SEARCH_SECONDS,
    GAME_VERSION,
    MISSION_CAPTURE_RADIUS,
    BULLET_DAMAGE,
    DASH_DIST,
    DYNAMIC_AOI_RADIUS_MAIN,
    DYNAMIC_AOI_RADIUS_ROOM,
    INPUT_IDLE_TIMEOUT,
    MAZE_CELL,
    MAZE_WALL,
    MAG_SIZE,
    MAX_ITEMS,
    MOVE_ACCEL,
    MOVE_COLLISION_STEP,
    MOVE_DECEL,
    PLAYER_MAX_HP,
    PLAYER_STAGE_LIVES,
    PLAYER_R,
    PLAYER_STALE_TIMEOUT,
    PROTOCOL_VERSION,
    RELOAD_SECONDS,
    SERVER_DT,
    MAX_RESERVE_BY_TYPE,
    START_AMMO_RESERVE,
    VEHICLE_SPEED_MULT,
    WEAPON_TYPES,
    ZOMBIE_TYPES,
)
from server_game.simulation import (
    FOG_SPAWNS_PER_TICK,
    Game,
    ROOM_FOG_SPAWNS_PER_TICK,
    ROOM_FOG_WAVE_MAX,
    ROOM_H,
    ROOM_W,
    SCENE_MAIN,
    player_speed,
)
from server_game.geometry import circ_rect


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
        game.wave_kills = 999
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

    def enter_room(self, game, room, now=None):
        now = game._now() if now is None else now
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": player.get("ack_seq", 0) + 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        self.assertNotEqual(player["scene"], SCENE_MAIN)
        return player

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
        self.assertEqual(game.players["p1"]["input_seq"], 2)
        self.assertEqual(game.players["p1"]["ack_seq"], 0)
        game.tick(SERVER_DT, now=game._now())
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
        self.assertIn(("p_leave", {"pid": "p1", "reason": "timeout", "sceneId": "main"}), events)

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
        self.assertEqual(game.players["p1"]["input_seq"], 7)
        self.assertEqual(game.players["p1"]["ack_seq"], 0)
        game.tick(SERVER_DT, now=game._now())
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

    def test_movement_resolves_overlap_inside_obstacle(self):
        game, _ = self.make_game()
        game.obstacles = [{"x": 100, "y": 80, "w": 80, "h": 80}]
        game._index_obstacles()

        x, y = game.move_col(130, 120, PLAYER_R, 0, 0)

        self.assertFalse(circ_rect(x, y, PLAYER_R, 100, 80, 80, 80))

    def test_movement_overlap_resolution_escapes_inside_corner(self):
        game, _ = self.make_game()
        game.obstacles = [
            {"x": 100, "y": 0, "w": 62, "h": 164},
            {"x": 0, "y": 100, "w": 164, "h": 62},
        ]
        game._index_obstacles()

        x, y = game.move_col(118, 118, PLAYER_R, 0, 0)

        self.assertFalse(game._overlaps_obstacle(x, y, PLAYER_R))

    def test_segment_expanded_rect_intersection_boundaries(self):
        obstacle = {"x": 100, "y": 100, "w": 60, "h": 50}

        self.assertTrue(Game._segment_hits_expanded_rect(60, 125, 220, 125, obstacle, 4))
        self.assertFalse(Game._segment_hits_expanded_rect(60, 92, 220, 92, obstacle, 4))
        self.assertTrue(Game._segment_hits_expanded_rect(60, 96, 220, 96, obstacle, 4))
        self.assertTrue(Game._segment_hits_expanded_rect(120, 120, 130, 130, obstacle, 4))

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

    def test_fire_uses_world_aim_target_after_moving(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        target_x = player["x"]
        target_y = player["y"] - 600

        game.handle_input(
            "p1",
            {
                "seq": 9,
                "keys": {"right": True},
                "aim_angle": 0,
                "aim_x": target_x,
                "aim_y": target_y,
                "fire": True,
                "shooting": False,
            },
        )
        self.tick_once(game)

        bullet = next(iter(game.bullets.values()))
        muzzle = WEAPON_TYPES["pistol"]["muzzle"]
        expected_angle = math.atan2(target_y - player["y"], target_x - player["x"])
        self.assertGreater(player["x"], target_x)
        self.assertAlmostEqual(math.atan2(bullet["vy"], bullet["vx"]), expected_angle, places=5)
        self.assertAlmostEqual(bullet["spawn_x"], player["x"] + math.cos(expected_angle) * muzzle, places=5)
        self.assertAlmostEqual(bullet["spawn_y"], player["y"] + math.sin(expected_angle) * muzzle, places=5)
        self.assertEqual(bullet["shot_seq"], 9)

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
        player["ammo_reserve"]["pistol"] = 0
        player["current_reserve"] = 0
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
        player["ammo_reserve"]["pistol"] = 12
        player["current_reserve"] = 12

        game.handle_input("p1", {"seq": 1, "aim_angle": 0, "shooting": True})
        self.tick_once(game)
        self.assertEqual(player["ammo"], 0)
        game.handle_input("p1", {"seq": 2, "reload": True})
        self.assertGreater(player["reload_until"], 0)
        game.tick(SERVER_DT, now=player["reload_until"] + RELOAD_SECONDS)

        self.assertEqual(player["ammo"], 12)
        self.assertEqual(player["ammo_reserve"]["pistol"], 0)
        self.assertEqual(player["current_reserve"], 0)
        self.assertTrue(any(ev == "reload_start" for ev, _ in events))
        self.assertTrue(any(ev == "reload_done" for ev, _ in events))

    def test_weapon_reserve_pools_are_split_by_ammo_type(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        now = game._now()
        start_pistol = player["ammo_reserve"]["pistol"]
        game._unlock_weapon(player, "rifle", now, notify=False)

        self.assertEqual(player["ammo_reserve"]["pistol"], start_pistol)
        self.assertGreater(player["ammo_reserve"]["rifle"], 0)

        game._switch_weapon("p1", player, "rifle", now, notify=False)
        player["ammo"] = 0
        game._try_reload("p1", player, now, manual=True)
        game.tick(SERVER_DT, now=player["reload_until"] + RELOAD_SECONDS)

        self.assertEqual(player["weapon_id"], "rifle")
        self.assertGreater(player["ammo"], 0)
        self.assertEqual(player["ammo_reserve"]["pistol"], start_pistol)
        self.assertLess(player["ammo_reserve"]["rifle"], WEAPON_TYPES["rifle"]["unlock_reserve"])

    def test_launcher_has_two_round_mag_and_separate_explosive_ammo(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        now = game._now()
        game._unlock_weapon(player, "launcher", now, notify=False)
        game._switch_weapon("p1", player, "launcher", now, notify=False)

        self.assertEqual(player["mag_size"], 3)
        self.assertEqual(player["ammo"], 3)
        self.assertEqual(player["ammo_reserve"]["explosive"], 0)

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
        game.zombies[1] = self.zombie(1, 1030, 1000, hp=18)
        game.zombies[2] = self.zombie(2, 1120, 1000, hp=18)
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

    def test_boss_resists_launcher_blast_and_enters_phase(self):
        game, events = self.make_game()
        now = game._now()
        game.wave = 3
        game.zombies[1] = self.zombie(1, 1000, 1000, hp=700, ztype="boss")
        game.zombies[1]["max_hp"] = 1000

        game._explode_projectile({
            "owner": "p1",
            "x": 1000,
            "y": 1000,
            "damage": 22,
            "explosion_radius": WEAPON_TYPES["launcher"]["explosion_radius"],
            "explosion_damage": WEAPON_TYPES["launcher"]["explosion_damage"],
            "boss_damage_mult": WEAPON_TYPES["launcher"]["boss_damage_mult"],
            "color": "#ff8844",
        }, now)
        game._maybe_boss_phase(1, game.zombies[1], now + SERVER_DT)

        self.assertIn(1, game.zombies)
        self.assertGreater(game.zombies[1]["hp"], 620)
        self.assertTrue(any(ev == "boss_rage" and data["phase"] == 1 for ev, data in events))

    def test_spitter_no_longer_damages_at_range(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["protect_until"] = 0
        player["shield_until"] = 0
        game.zombies[1] = self.zombie(1, 660, 1000, hp=80, ztype="spitter")

        game.tick(SERVER_DT, now=now)

        self.assertEqual(player["hp"], PLAYER_MAX_HP)
        self.assertFalse(any(ev == "z_spit" for ev, _ in events))

    def test_facility_rooms_apply_gameplay_effects(self):
        game, events = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "medbay")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.pending_fog_spawns.clear()
        events.clear()
        player["hp"] = 52

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS, now + 1.0)

        self.assertEqual(player["hp"], 52)
        self.assertEqual(player["facility_label"], "病房")
        self.assertIn("医疗物资", player["facility_status"])
        room_items = [item for item in game.items.values() if item.get("scene") == scene_id]
        self.assertGreaterEqual(len(room_items), 2)
        self.assertTrue(any(item["type"] == "medkit" for item in room_items))
        self.assertTrue(any(ev == "facility_used" and data["facility"] == "medbay" for ev, data in events))

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

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS, now)

        self.assertEqual(game.task_counts["fuse"], 0)
        self.assertTrue(game.extractions[0]["visible"])
        self.assertTrue(any(ev == "mission_revealed" for ev, _ in events))
        self.assertTrue(any(ev == "facility_used" for ev, _ in events))
        self.assertFalse(any(ev == "fog_wave" and data["reason"] == "generator" for ev, data in events))

    def test_lab_entry_triggers_fog_pressure(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]

        game._apply_facility_effects(SERVER_DT, now + SERVER_DT)

        self.assertEqual(player["facility_label"], "样本库")
        self.assertGreater(game.lab_sample_until, now)
        self.assertTrue(room["alarm_spawned"])
        self.assertIn("样本共振", player["facility_status"])
        self.assertTrue(any(ev == "lab_reactor" for ev, _ in events))
        self.assertTrue(any(ev == "fog_wave" and data["reason"] == "lab" and data["sceneId"] == scene_id for ev, data in events))

    def test_lab_search_drops_sample_item_without_counting_it(self):
        game, _ = self.make_game()
        now = game._now()
        game.items.clear()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.pending_fog_spawns.clear()

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS * 1.1, now + 1.0)

        sample_items = [
            item for item in game.items.values()
            if item["type"] == "sample" and item.get("scene") == scene_id
        ]
        self.assertTrue(room["searched"])
        self.assertEqual(len(sample_items), 1)
        self.assertGreaterEqual(
            len([item for item in game.items.values() if item.get("scene") == scene_id]),
            2,
        )
        self.assertEqual(game.task_counts.get("sample", 0), 0)

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
        self.assertTrue(any(item["type"].startswith("ammo_") or item["type"] == "ammo" for item in game.items.values()))
        self.assertTrue(any(ev == "facility_used" for ev, _ in events))
        item_count = len(game.items)

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS + 0.05, now + 1)

        self.assertTrue(room["searched"])
        self.assertEqual(len(game.items), item_count)

    def test_security_room_requires_keycard_then_drops_reward_item(self):
        game, events = self.make_game()
        now = game._now()
        game.items.clear()
        room = next(feature for feature in game.map_features if feature.get("effect") == "security")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.task_counts["keycard"] = 1
        game.pending_fog_spawns.clear()
        events.clear()

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS + 0.05, now + 1.0)

        self.assertTrue(room["searched"])
        self.assertEqual(game.task_counts["keycard"], 0)
        self.assertTrue(any(item.get("scene") == scene_id for item in game.items.values()))
        self.assertTrue(any(ev == "task_update" and data["type"] == "keycard" for ev, data in events))

    def test_security_room_triggers_one_fog_alarm_per_search(self):
        game, events = self.make_game()
        now = game._now()
        game.items.clear()
        room = next(feature for feature in game.map_features if feature.get("effect") == "security")
        self.enter_room(game, room, now)
        game.task_counts["keycard"] = 1
        events.clear()

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS + 0.05, now + 1.0)

        fog_events = [
            data for ev, data in events
            if ev == "fog_wave" and data.get("reason") == "security"
        ]
        self.assertEqual(len(fog_events), 0)
        self.assertTrue(room["alarm_spawned"])

    def test_morgue_search_drops_sample_item(self):
        game, _ = self.make_game()
        now = game._now()
        game.items.clear()
        room = next(feature for feature in game.map_features if feature.get("effect") == "morgue")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.pending_fog_spawns.clear()
        player["hp"] = 80

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS, now + 11.0)

        self.assertTrue(room["searched"])
        self.assertTrue(
            any(item["type"] == "sample" and item.get("scene") == scene_id for item in game.items.values())
        )
        self.assertTrue(any(item.get("scene") == scene_id and item["type"] != "sample" for item in game.items.values()))
        self.assertLess(player["hp"], 80)

    def test_archive_search_drops_lore_item_once_before_counting_lore(self):
        game, events = self.make_game()
        now = game._now()
        game.items.clear()
        room = next(feature for feature in game.map_features if feature.get("effect") == "archive")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.pending_fog_spawns.clear()
        events.clear()

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS * 1.18 + 0.05, now + 1.0)

        lore_items = [
            item for item in game.items.values()
            if item["type"] == "lore" and item.get("scene") == scene_id
        ]
        self.assertTrue(room["searched"])
        self.assertEqual(len(lore_items), 1)
        self.assertEqual(player.get("lore", 0), 0)
        self.assertFalse(any(ev == "lore_found" for ev, _ in events))
        item_count = len(game.items)

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS * 1.18 + 0.05, now + 2.0)

        self.assertEqual(len(game.items), item_count)

    def test_archive_room_triggers_one_fog_alarm_per_search(self):
        game, events = self.make_game()
        now = game._now()
        game.items.clear()
        room = next(feature for feature in game.map_features if feature.get("effect") == "archive")
        self.enter_room(game, room, now)
        events.clear()

        game._apply_facility_effects(FACILITY_SEARCH_SECONDS * 1.18 + 0.05, now + 1.0)

        fog_events = [
            data for ev, data in events
            if ev == "fog_wave" and data.get("reason") == "archive"
        ]
        self.assertEqual(len(fog_events), 0)
        self.assertTrue(room["alarm_spawned"])

    def test_forced_room_rewards_keep_global_item_cap(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "armory")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.items = {
            iid: {
                "id": iid,
                "x": 100 + iid * 12,
                "y": 100,
                "type": "ammo",
                "scene": SCENE_MAIN,
            }
            for iid in range(1, MAX_ITEMS + 1)
        }
        game._next_i = MAX_ITEMS + 1

        game._spawn_item_in_feature(room, "weapon_rifle", emit=False, scene=scene_id)
        game._spawn_item_in_feature(room, "ammo_rifle", emit=False, scene=scene_id)

        self.assertEqual(len(game.items), MAX_ITEMS)
        self.assertTrue(any(item.get("type") == "weapon_rifle" for item in game.items.values()))
        self.assertTrue(any(item.get("type") == "ammo_rifle" for item in game.items.values()))

    def test_armory_keeps_pending_reward_if_primary_spawn_fails(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "armory")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        room["pending_reward"] = "weapon_rifle"
        original_spawn = game._spawn_item_in_feature
        calls = []

        def fail_primary(feature, item_type, *args, **kwargs):
            calls.append(item_type)
            if len(calls) == 1:
                return None
            return original_spawn(feature, item_type, *args, **kwargs)

        game._spawn_item_in_feature = fail_primary
        spawned = game._spawn_room_rewards(room, "armory", player, scene_id)

        self.assertTrue(spawned)
        self.assertEqual(room.get("pending_reward"), "weapon_rifle")

        game._spawn_item_in_feature = original_spawn
        spawned = game._spawn_room_rewards(room, "armory", player, scene_id)

        self.assertTrue(spawned)
        self.assertNotIn("pending_reward", room)

    def test_armory_persists_unseeded_reward_if_primary_spawn_fails(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "armory")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        room.pop("pending_reward", None)
        original_spawn = game._spawn_item_in_feature
        reward_rolls = []
        spawn_calls = []

        def roll_reward(current_player):
            reward_rolls.append(current_player["id"])
            return "weapon_rifle"

        def fail_primary(feature, item_type, *args, **kwargs):
            spawn_calls.append(item_type)
            if len(spawn_calls) == 1:
                return None
            return original_spawn(feature, item_type, *args, **kwargs)

        game._armory_reward_type = roll_reward
        game._spawn_item_in_feature = fail_primary

        game._spawn_room_rewards(room, "armory", player, scene_id)

        self.assertEqual(reward_rolls, ["p1"])
        self.assertEqual(room.get("pending_reward"), "weapon_rifle")

        def should_not_reroll(current_player):
            raise AssertionError("pending armory reward should be reused")

        game._armory_reward_type = should_not_reroll
        game._spawn_item_in_feature = original_spawn

        spawned = game._spawn_room_rewards(room, "armory", player, scene_id)

        self.assertTrue(spawned)
        self.assertTrue(any(game.items[iid]["type"] == "weapon_rifle" for iid in spawned))
        self.assertNotIn("pending_reward", room)

    def test_lore_pickup_increments_lore_and_emits_story_once(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        item = {
            "id": 77,
            "x": player["x"],
            "y": player["y"],
            "type": "lore",
            "color": "#aee6ff",
            "icon": "D",
            "name": "档案碎片",
            "radius": 15,
            "scene": SCENE_MAIN,
        }

        game._apply_item("p1", item, now)

        self.assertEqual(player["lore"], 1)
        self.assertTrue(any(ev == "lore_found" and data["count"] == 1 for ev, data in events))
        self.assertTrue(any(ev == "item_pick" and data["type"] == "lore" for ev, data in events))

    def test_objective_items_remain_visible_across_room_aoi(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        player["x"] = 120
        player["y"] = 120
        game.items[1] = {
            "id": 1,
            "x": ROOM_W - 120,
            "y": ROOM_H - 120,
            "type": "lore",
            "color": "#aee6ff",
            "icon": "D",
            "name": "档案碎片",
            "radius": 15,
            "scene": scene_id,
        }
        game.items[2] = dict(game.items[1], id=2, type="parts", color="#8fd0ff", icon="P", name="武器零件")

        snap = game.get_snapshot("p1")

        self.assertIn(1, snap["i"])
        self.assertNotIn(2, snap["i"])
        self.assertLess(snap["perf"]["payload_max_bytes"], 8000)

    def test_dangerous_room_hazard_damages_only_current_scene_player(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        player["facility_room_id"] = room["id"]
        player["hp"] = 80
        room["alarm_spawned"] = True
        game.pending_fog_spawns.clear()

        game._apply_facility_effects(1.0, now + 11.0)

        self.assertLess(player["hp"], 80)
        hp_after_room = player["hp"]
        player["scene"] = SCENE_MAIN
        game._apply_room_hazard("p1", player, scene_id, "lab", 1.0, now + 12.0)

        self.assertEqual(player["hp"], hp_after_room)

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
        self.assertEqual(snap["p"]["p1"][14], 0)

        game.tick(SERVER_DT, now=game._now())
        snap = game.get_snapshot()
        self.assertEqual(snap["p"]["p1"][14], 3)
        player_tuple = snap["p"]["p1"]
        self.assertEqual(len(player_tuple), 43)
        self.assertEqual(player_tuple[24], START_AMMO_RESERVE["pistol"])
        self.assertIn("pistol:", player_tuple[36])
        self.assertEqual(player_tuple[37], "pistol")
        self.assertEqual(player_tuple[39], PLAYER_STAGE_LIVES)
        self.assertEqual(player_tuple[41], "main")
        self.assertIn("perf", snap)
        self.assertIn("tick_ms", snap["perf"])
        self.assertIn("payload_bytes", snap["perf"])
        self.assertIn("overlap_resolves", snap["perf"])
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

    def test_room_snapshot_shrinks_dynamic_aoi_and_keeps_own_bullets(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        scene_id = player["scene"]
        player["x"] = 300
        player["y"] = 590
        near_zid = game.spawn_zombie(x=player["x"] + DYNAMIC_AOI_RADIUS_ROOM - 40, y=player["y"], ztype="runner", scene=scene_id)
        far_zid = game.spawn_zombie(x=player["x"] + DYNAMIC_AOI_RADIUS_ROOM + 150, y=player["y"], ztype="runner", scene=scene_id)
        main_zid = game.spawn_zombie(x=player.get("main_x", 1000), y=player.get("main_y", 1000), ztype="runner", scene="main")
        game.bullets[1] = {
            "id": 1,
            "owner": "p1",
            "weapon": "pistol",
            "scene": scene_id,
            "x": player["x"] + DYNAMIC_AOI_RADIUS_ROOM + 180,
            "y": player["y"],
            "vx": 760,
            "vy": 0,
            "radius": 4.2,
            "life": 0.6,
            "color": "#ffffff",
        }
        game.bullets[2] = dict(game.bullets[1], id=2, owner="p2", x=player["x"] + DYNAMIC_AOI_RADIUS_ROOM + 190)

        snap = game.get_snapshot("p1")

        self.assertIn(near_zid, snap["z"])
        self.assertNotIn(far_zid, snap["z"])
        self.assertNotIn(main_zid, snap["z"])
        self.assertEqual(snap["zt"], 2)
        self.assertIn(1, snap["b"])
        self.assertNotIn(2, snap["b"])
        self.assertEqual(snap["dynamicAoi"], DYNAMIC_AOI_RADIUS_ROOM)
        self.assertLess(snap["perf"]["payload_max_bytes"], 8000)

    def test_snapshot_zombie_total_is_scoped_to_viewer_scene(self):
        game, _ = self.make_game()
        game.zombies.clear()
        game.add_player("p2")
        room_scene = next(iter(game.room_scenes))
        room_player = game.players["p2"]
        room_player["scene"] = room_scene
        room_player["x"] = 320
        room_player["y"] = 560

        for idx in range(2):
            game.spawn_zombie(x=1000 + idx * 40, y=1000, ztype="runner", scene=SCENE_MAIN)
        for idx in range(3):
            game.spawn_zombie(x=360 + idx * 34, y=560, ztype="runner", scene=room_scene)

        self.assertEqual(game.get_snapshot("p1")["zt"], 2)
        self.assertEqual(game.get_snapshot("p2")["zt"], 3)

    def test_dynamic_aoi_radius_uses_main_and_room_values(self):
        game, _ = self.make_game()
        room_scene = next(scene_id for scene_id in game.room_scenes)

        self.assertEqual(game._dynamic_aoi_radius(SCENE_MAIN), DYNAMIC_AOI_RADIUS_MAIN)
        self.assertEqual(game._dynamic_aoi_radius(room_scene), DYNAMIC_AOI_RADIUS_ROOM)

    def test_init_data_exposes_authoritative_tuning(self):
        game, _ = self.make_game()
        init = game.get_init_data("p1", game.players["p1"]["idx"])

        self.assertEqual(init["cfg"]["gameVersion"], GAME_VERSION)
        self.assertEqual(init["cfg"]["playerSpeed"], 315)
        self.assertEqual(init["cfg"]["dashDist"], DASH_DIST)
        self.assertEqual(init["cfg"]["moveAccel"], MOVE_ACCEL)
        self.assertEqual(init["cfg"]["moveDecel"], MOVE_DECEL)
        self.assertEqual(init["cfg"]["moveCollisionStep"], MOVE_COLLISION_STEP)
        self.assertEqual(init["cfg"]["dynamicAoiRoom"], DYNAMIC_AOI_RADIUS_ROOM)
        self.assertEqual(init["cfg"]["playerMaxHp"], PLAYER_MAX_HP)
        self.assertEqual(init["dynamicAoi"], init["cfg"]["dynamicAoiMain"])
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
        self.assertEqual(game.players["p1"]["current_reserve"], START_AMMO_RESERVE["pistol"])
        self.assertEqual(game.players["p1"]["ammo_reserve"]["pistol"], START_AMMO_RESERVE["pistol"])
        self.assertIn("maxReserveByType", init["cfg"])
        self.assertIn("ammoTypeLabels", init["cfg"])

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

    def test_entering_facility_switches_to_indoor_scene_and_returns(self):
        game, events = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2

        game._apply_facility_effects(SERVER_DT, now)

        self.assertEqual(player["scene"], "main")
        self.assertEqual(player["facility_status"], f"按 F 进入{room['label']}")
        self.assertTrue(any(ev == "facility_pulse" and "按 F" in data["text"] for ev, data in events))

        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now + SERVER_DT)

        scene_id = player["scene"]
        self.assertTrue(scene_id.startswith("room:"))
        self.assertEqual(player["room_id"], room["id"])
        self.assertTrue(any(ev == "scene_change" and data["reason"] == "enter_room" for ev, data in events))
        snap = game.get_snapshot("p1")
        self.assertEqual(snap["scene"], scene_id)
        self.assertEqual(snap["sceneName"], room["label"])
        self.assertLess(snap["mw"], 3000)

        game._apply_facility_effects(SERVER_DT, now + SERVER_DT)
        self.assertEqual(player["scene"], scene_id)

        scene = game.room_scenes[scene_id]
        player["x"] = scene["exit"]["x"]
        player["y"] = scene["exit"]["y"]
        game._apply_facility_effects(SERVER_DT, now + 1.0)

        self.assertEqual(player["scene"], "main")
        self.assertEqual(player["room_id"], "")
        self.assertFalse(any(
            circ_rect(player["x"], player["y"], PLAYER_R, obstacle["x"], obstacle["y"], obstacle["w"], obstacle["h"])
            for obstacle in game._near_obstacles(player["x"], player["y"], PLAYER_R + MAZE_WALL + 4)
        ))
        game._apply_facility_effects(SERVER_DT, now + 3.0)
        self.assertEqual(player["scene"], "main")
        self.assertTrue(any(ev == "scene_change" and data["reason"] == "leave_room" for ev, data in events))

    def test_interact_input_clears_inside_room_without_exit(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        scene_id = player["scene"]
        scene = game.room_scenes[scene_id]
        player["x"] = scene["mw"] * 0.5
        player["y"] = scene["mh"] * 0.5

        game.handle_input("p1", {"seq": 2, "interact": True})
        game._apply_facility_effects(SERVER_DT, now + SERVER_DT)

        self.assertEqual(player["scene"], scene_id)
        self.assertFalse(player["interact_requested"])

    def test_facility_notice_dedupes_repeated_entry_prompt(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["facility_room_id"] = "medbay-a"

        game._facility_notice(player, now, "按 F 进入病房", notice_key="enter_prompt")
        game._facility_notice(player, now + 1.5, "按 F 进入病房", notice_key="enter_prompt")

        pulses = [data for ev, data in events if ev == "facility_pulse"]
        self.assertEqual(len(pulses), 1)

        player["facility_room_id"] = "lab-b"
        game._facility_notice(player, now + 1.6, "按 F 进入样本库", notice_key="enter_prompt")

        pulses = [data for ev, data in events if ev == "facility_pulse"]
        self.assertEqual(len(pulses), 2)
        self.assertEqual(pulses[-1]["text"], "按 F 进入样本库")

    def test_room_scene_spawns_are_not_blocked_or_on_exit(self):
        game, _ = self.make_game()
        for scene_id, scene in game.room_scenes.items():
            with self.subTest(scene=scene_id):
                sx, sy = scene["spawn"]
                exit_point = scene["exit"]
                exit_dist = math.hypot(sx - exit_point["x"], sy - exit_point["y"])
                self.assertGreater(exit_dist, exit_point["radius"] + PLAYER_R + 8)
                self.assertFalse(any(
                    circ_rect(sx, sy, PLAYER_R, obstacle["x"], obstacle["y"], obstacle["w"], obstacle["h"])
                    for obstacle in scene["obs"]
                ))

    def test_room_return_point_prefers_original_entry_position(self):
        game, _ = self.make_game()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = {
            "main_x": room["x"] + room["w"] / 2,
            "main_y": room["y"] + room["h"] / 2,
        }

        x, y = game._room_return_point(room, player)

        main_scene = game._scene_def("main")
        self.assertGreaterEqual(x, PLAYER_R)
        self.assertGreaterEqual(y, PLAYER_R)
        self.assertLessEqual(x, main_scene["mw"] - PLAYER_R)
        self.assertLessEqual(y, main_scene["mh"] - PLAYER_R)
        self.assertAlmostEqual(x, player["main_x"], delta=0.1)
        self.assertAlmostEqual(y, player["main_y"], delta=0.1)
        self.assertFalse(game._overlaps_obstacle(x, y, PLAYER_R))

    def test_room_return_point_resolves_blocked_entry_without_cross_wall_floor_jump(self):
        game, _ = self.make_game()
        room = {
            "kind": "room",
            "id": "wall-adjacent-room",
            "x": 900,
            "y": 900,
            "w": 180,
            "h": 160,
        }
        player = {"main_x": 900 + PLAYER_R * 0.4, "main_y": 980}
        game.obstacles = [{"x": 760, "y": 850, "w": 110, "h": 260}]
        game._index_obstacles()
        game.floor_points = [(700, 980), (930, 980), (1140, 980)]

        x, y = game._room_return_point(room, player)

        self.assertGreater(x, 870)
        self.assertLess(abs(y - player["main_y"]), 80)
        self.assertFalse(game._overlaps_obstacle(x, y, PLAYER_R))

    def test_indoor_scene_entities_are_isolated_and_zombies_move(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        scene_id = player["scene"]

        main_zid = game.spawn_zombie(x=player.get("main_x", 1000), y=player.get("main_y", 1000), ztype="walker", scene="main")
        room_zid = game.spawn_zombie(x=player["x"] + DYNAMIC_AOI_RADIUS_ROOM - 120, y=player["y"], ztype="runner", scene=scene_id)
        main_item = game.spawn_item(x=player.get("main_x", 1000), y=player.get("main_y", 1000), item_type="parts", scene="main")
        room_item = game.spawn_item(x=500, y=500, item_type="parts", scene=scene_id)

        self.assertIsNotNone(main_zid)
        self.assertIsNotNone(room_zid)
        self.assertIsNotNone(main_item)
        self.assertIsNotNone(room_item)

        snap = game.get_snapshot("p1")

        self.assertIn(room_zid, snap["z"])
        self.assertNotIn(main_zid, snap["z"])
        self.assertIn(room_item, snap["i"])
        self.assertNotIn(main_item, snap["i"])

        old_x = game.zombies[room_zid]["x"]
        old_y = game.zombies[room_zid]["y"]
        game._update_zombies(SERVER_DT, now + SERVER_DT)

        room_zombie = game.zombies[room_zid]
        self.assertGreater(math.hypot(room_zombie["x"] - old_x, room_zombie["y"] - old_y), 0.1)

    def test_indoor_zombie_routes_around_room_bulkhead(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        scene_id = player["scene"]
        player["x"] = 300
        player["y"] = 590
        player["protect_until"] = now + 99
        zid = game.spawn_zombie(x=1500, y=590, ztype="runner", scene=scene_id)
        start_dist = math.hypot(game.zombies[zid]["x"] - player["x"], game.zombies[zid]["y"] - player["y"])

        for i in range(140):
            game._update_zombies(SERVER_DT, now + i * SERVER_DT)

        zombie = game.zombies[zid]
        end_dist = math.hypot(zombie["x"] - player["x"], zombie["y"] - player["y"])
        self.assertLess(end_dist, start_dist * 0.58)
        self.assertLess(zombie["x"], 1045)

    def test_indoor_zombie_visibility_graph_does_not_stack_on_wall(self):
        game, _ = self.make_game()
        now = game._now()
        scene_id = next(iter(game.room_scenes))
        scene = game.room_scenes[scene_id]
        bulkhead = next(obstacle for obstacle in scene["obs"] if obstacle.get("kind") == "bulkhead")
        player = game.players["p1"]
        player["scene"] = scene_id
        player["scene_name"] = scene["name"]
        player["x"] = bulkhead["x"] + bulkhead["w"] + 170
        player["y"] = bulkhead["y"] + bulkhead["h"] / 2
        player["protect_until"] = now + 99
        zids = [
            game.spawn_zombie(
                x=bulkhead["x"] - 175 - index * 16,
                y=player["y"] + (index - 2) * 34,
                ztype="runner",
                scene=scene_id,
            )
            for index in range(5)
        ]
        start_avg = sum(math.hypot(game.zombies[zid]["x"] - player["x"], game.zombies[zid]["y"] - player["y"]) for zid in zids) / len(zids)

        for i in range(260):
            game._update_zombies(SERVER_DT, now + i * SERVER_DT)

        zombies = [game.zombies[zid] for zid in zids]
        end_avg = sum(math.hypot(zombie["x"] - player["x"], zombie["y"] - player["y"]) for zombie in zombies) / len(zombies)
        crossed = [zombie for zombie in zombies if zombie["x"] > bulkhead["x"] + bulkhead["w"] + 34]
        self.assertLess(end_avg, start_avg * 0.64)
        self.assertGreaterEqual(len(crossed), 1)
        self.assertFalse(any(
            circ_rect(zombie["x"], zombie["y"], zombie["radius"], bulkhead["x"], bulkhead["y"], bulkhead["w"], bulkhead["h"])
            for zombie in zombies
        ))
        self.assertTrue(game.room_nav_cache)
        cache_ids = {key: id(value) for key, value in game.room_nav_cache.items()}

        game._update_zombies(SERVER_DT, now + 261 * SERVER_DT)

        self.assertEqual(cache_ids, {key: id(value) for key, value in game.room_nav_cache.items()})

    def test_indoor_zombie_pathfinder_reuses_cached_route_between_repath_ticks(self):
        game, _ = self.make_game()
        now = game._now()
        scene_id = next(iter(game.room_scenes))
        scene = game.room_scenes[scene_id]
        bulkhead = next(obstacle for obstacle in scene["obs"] if obstacle.get("kind") == "bulkhead")
        player = game.players["p1"]
        player["scene"] = scene_id
        player["scene_name"] = scene["name"]
        player["x"] = bulkhead["x"] + bulkhead["w"] + 170
        player["y"] = bulkhead["y"] + bulkhead["h"] / 2
        player["protect_until"] = now + 20
        game.zombies.clear()

        for index in range(8):
            game.spawn_zombie(
                x=bulkhead["x"] - 175 - index * 16,
                y=player["y"] + (index - 3) * 26,
                ztype="runner",
                scene=scene_id,
            )

        original = game._room_visibility_path
        calls = 0

        def counted_visibility_path(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        game._room_visibility_path = counted_visibility_path
        for frame in range(30):
            game._update_zombies(SERVER_DT, now + frame * SERVER_DT)

        self.assertGreater(calls, 0)
        self.assertLessEqual(calls, 12)

    def test_room_direct_path_invalidates_when_los_becomes_blocked(self):
        game, _ = self.make_game()
        now = game._now()
        scene_id = "room-test-los"
        scene = {
            "id": scene_id,
            "name": "视线测试房",
            "mw": 1000,
            "mh": 720,
            "obs": [],
            "features": [],
            "nav_points": [(420, 170), (640, 170), (420, 550), (640, 550)],
        }
        game.room_scenes[scene_id] = scene
        zombie = {"id": 902, "x": 280, "y": 360, "radius": 18, "scene": scene_id}
        target = {"id": "p1", "x": 760, "y": 360, "radius": PLAYER_R, "scene": scene_id}

        game._room_zombie_waypoint(zombie, target, now)

        self.assertEqual(zombie.get("path_kind"), "room_direct")

        scene["obs"].append({"x": 485, "y": 250, "w": 70, "h": 220, "kind": "bulkhead"})
        waypoint = game._room_zombie_waypoint(zombie, target, now + SERVER_DT)

        self.assertEqual(zombie.get("path_kind"), "room")
        self.assertEqual(zombie.get("path_source"), "visibility")
        self.assertNotEqual((waypoint["x"], waypoint["y"]), (target["x"], target["y"]))

    def test_indoor_zombie_recovers_from_fallback_to_visibility_path(self):
        game, _ = self.make_game()
        now = game._now()
        scene_id = "room-test-recover"
        game.room_scenes[scene_id] = {
            "id": scene_id,
            "name": "恢复测试房",
            "mw": 1000,
            "mh": 720,
            "obs": [{"x": 485, "y": 250, "w": 70, "h": 220, "kind": "bulkhead"}],
            "features": [],
            "nav_points": [(420, 170), (640, 170), (420, 550), (640, 550)],
        }
        zombie = {"id": 903, "x": 280, "y": 360, "radius": 18, "scene": scene_id}
        target = {"id": "p1", "x": 760, "y": 360, "radius": PLAYER_R, "scene": scene_id}
        old_budget = simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK
        simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK = 0
        try:
            game._room_zombie_waypoint(zombie, target, now)
        finally:
            simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK = old_budget

        self.assertEqual(zombie.get("path_source"), "fallback")

        game._room_path_recomputes_this_tick = 0
        game._room_zombie_waypoint(zombie, target, zombie["path_retry_at"] + SERVER_DT)

        self.assertEqual(zombie.get("path_source"), "visibility")

    def test_indoor_zombie_fallback_moves_when_recompute_budget_is_exhausted(self):
        game, _ = self.make_game()
        now = game._now()
        scene_id = next(iter(game.room_scenes))
        scene = game.room_scenes[scene_id]
        bulkhead = next(obstacle for obstacle in scene["obs"] if obstacle.get("kind") == "bulkhead")
        player = game.players["p1"]
        player["scene"] = scene_id
        player["scene_name"] = scene["name"]
        player["x"] = bulkhead["x"] + bulkhead["w"] + 170
        player["y"] = bulkhead["y"] + bulkhead["h"] / 2
        player["protect_until"] = now + 20
        game.zombies.clear()
        zid = game.spawn_zombie(
            x=bulkhead["x"] - 190,
            y=player["y"],
            ztype="runner",
            scene=scene_id,
        )
        start = (game.zombies[zid]["x"], game.zombies[zid]["y"])
        old_budget = simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK
        simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK = 0
        try:
            game._update_zombies(SERVER_DT, now)
        finally:
            simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK = old_budget

        zombie = game.zombies[zid]
        self.assertEqual(zombie.get("path_source"), "fallback")
        self.assertGreater(math.hypot(zombie["x"] - start[0], zombie["y"] - start[1]), 0.1)

    def test_indoor_zombie_waits_when_no_safe_room_route_exists(self):
        game, _ = self.make_game()
        now = game._now()
        scene_id = "room-test-blocked"
        wall = {"x": 500, "y": 0, "w": 90, "h": 900, "kind": "bulkhead"}
        game.room_scenes[scene_id] = {
            "id": scene_id,
            "name": "封闭测试房",
            "mw": 1000,
            "mh": 900,
            "obs": [wall],
            "features": [],
            "nav_points": [],
        }
        zombie = {
            "id": 901,
            "x": 330,
            "y": 450,
            "radius": 18,
            "scene": scene_id,
        }
        target = {
            "id": "p1",
            "x": 760,
            "y": 450,
            "radius": PLAYER_R,
            "scene": scene_id,
        }
        old_budget = simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK
        simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK = 0
        try:
            waypoint = game._room_zombie_waypoint(zombie, target, now)
        finally:
            simulation_module.ROOM_PATH_RECOMPUTES_PER_TICK = old_budget

        self.assertEqual(zombie.get("path_source"), "blocked")
        self.assertAlmostEqual(waypoint["x"], zombie["x"])
        self.assertAlmostEqual(waypoint["y"], zombie["y"])

    def test_room_nav_cache_can_invalidate_one_scene(self):
        game, _ = self.make_game()
        scene_ids = list(game.room_scenes.keys())[:2]
        self.assertGreaterEqual(len(scene_ids), 2)
        first = game._room_nav_graph(scene_ids[0], 24)
        second = game._room_nav_graph(scene_ids[1], 24)

        game._invalidate_room_nav_cache(scene_ids[0])

        self.assertNotIn((scene_ids[0], 24), game.room_nav_cache)
        self.assertIs(game.room_nav_cache[(scene_ids[1], 24)], second)
        self.assertIsNot(game._room_nav_graph(scene_ids[0], 24), first)

    def test_indoor_bullet_kill_emits_room_scene_effects(self):
        game, events = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        scene_id = player["scene"]
        player["x"] = 500
        player["y"] = 500
        player["aim_x"] = 650
        player["aim_y"] = 500
        player["aim_angle"] = 0
        player["protect_until"] = now + 99
        zid = game.spawn_zombie(x=650, y=500, ztype="walker", scene=scene_id)
        game.zombies[zid]["hp"] = BULLET_DAMAGE

        game.handle_input("p1", {"seq": 2, "aim_angle": 0, "aim_x": 650, "aim_y": 500, "fire": True})
        for i in range(10):
            game.tick(SERVER_DT, now=now + (i + 1) * SERVER_DT)
            if zid not in game.zombies:
                break

        deaths = [data for ev, data in events if ev == "z_die" and data.get("zid") == zid]
        self.assertTrue(deaths)
        self.assertEqual(deaths[-1]["sceneId"], scene_id)
        self.assertIn("p1", deaths[-1]["_targets"])

    def test_main_scene_bloater_explosion_does_not_damage_indoor_player(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        player["hp"] = PLAYER_MAX_HP
        player["protect_until"] = 0
        zombie = self.zombie(9, player.get("main_x", 1000), player.get("main_y", 1000), hp=1, ztype="bloater")
        zombie["scene"] = "main"
        game.zombies[9] = zombie

        game._explode_bloater("p1", 9, zombie, now)

        self.assertEqual(player["hp"], PLAYER_MAX_HP)

    def test_direct_player_damage_respects_source_scene(self):
        game, _ = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["scene"] = "room:test"
        player["hp"] = PLAYER_MAX_HP
        player["protect_until"] = 0
        player["shield_until"] = 0

        game._damage_player("p1", 25, now, source="test", source_scene="main")

        self.assertEqual(player["hp"], PLAYER_MAX_HP)

        game._damage_player("p1", 25, now, source="test", source_scene="room:test")

        self.assertEqual(player["hp"], PLAYER_MAX_HP - 25)

    def test_main_scene_respawn_event_is_not_sent_to_indoor_players(self):
        game, events = self.make_game()
        now = game._now()
        game.add_player("p2")
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        indoor = game.players["p1"]
        indoor["x"] = room["x"] + room["w"] / 2
        indoor["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        game.players["p2"]["dead"] = True

        game._respawn_player("p2", game.players["p2"], now)

        respawns = [data for ev, data in events if ev == "p_resp" and data.get("pid") == "p2"]
        self.assertTrue(respawns)
        self.assertEqual(respawns[-1]["sceneId"], "main")
        self.assertNotIn("p1", respawns[-1].get("_targets", []))
        self.assertIn("p2", respawns[-1].get("_targets", []))

    def test_main_scene_respawn_event_is_aoi_scoped_for_remote_players(self):
        game, events = self.make_game()
        now = game._now()
        game.add_player("p2")
        game.add_player("p3")
        game.safe_player_spawn = lambda: (1000, 1000)
        game.players["p1"]["x"] = 1040
        game.players["p1"]["y"] = 1000
        game.players["p3"]["x"] = 2600
        game.players["p3"]["y"] = 2600
        game.players["p2"]["dead"] = True

        game._respawn_player("p2", game.players["p2"], now)

        respawn = [data for ev, data in events if ev == "p_resp" and data.get("pid") == "p2"][-1]
        targets = set(respawn.get("_targets", []))
        self.assertIn("p1", targets)
        self.assertIn("p2", targets)
        self.assertNotIn("p3", targets)

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
        game.wave_kills = 999
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
        player["ammo_reserve"]["pistol"] = 10
        game._sync_weapon_fields(player)
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
        game.wave_kills = 999

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)

        self.assertGreater(player["ammo_reserve"]["pistol"], 10)
        self.assertGreater(player["ammo_reserve"]["rifle"], 0)
        self.assertGreater(player["ammo_reserve"]["smg"], 0)
        self.assertGreater(player["ammo_reserve"]["shell"], 0)
        self.assertLessEqual(player["ammo_reserve"]["pistol"], MAX_RESERVE_BY_TYPE["pistol"])
        complete = [data for ev, data in events if ev == "mission_complete"][-1]
        self.assertEqual(complete["rewardTitle"], "弹药缓存")
        self.assertIn("手枪弹", complete["rewardText"])
        self.assertIsNotNone(game.intermission)

        game.continue_intermission("p1")

        started = [data for ev, data in events if ev == "wave_start"][-1]
        self.assertEqual(started["routeReward"]["route"], "service")
        self.assertIn("features", started)

    def test_archive_extraction_requires_lore_and_grants_high_value_reward(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        exit_point = {
            "id": "archive-reward",
            "type": "archive",
            "name": "档案门",
            "text": "拼合黑匣档案",
            "requires": {"lore": 1, "sample": 1},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.99,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#ff8fb6",
            "rewardTitle": "档案门",
            "rewardText": "高危撤离：全队获得爆破弹 +1、保护罩掉落，并额外拼合档案线索。",
            "shortReward": "爆破弹/护盾/线索",
        }
        game.extractions = [exit_point]
        game.mission = exit_point
        game.task_counts["sample"] = 1

        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now)
        self.assertIsNone(game.intermission)
        self.assertLess(exit_point["charge"], 1)

        player["lore"] = 1
        game._update_mission(EXTRACTION_CAPTURE_SECONDS, now + 1)

        self.assertIsNotNone(game.intermission)
        self.assertGreaterEqual(player["ammo_reserve"]["explosive"], 1)
        self.assertGreater(player["shield_until"], now)
        complete = [data for ev, data in events if ev == "mission_complete"][-1]
        self.assertEqual(complete["rewardTitle"], "档案门")
        fog_events = [
            data for ev, data in events
            if ev == "fog_wave" and data.get("reason") == "archive"
        ]
        self.assertEqual(len(fog_events), 1)

    def test_stage_wipes_after_lives_are_exhausted(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["protect_until"] = 0
        player["lives"] = 0

        game._kill_player("p1", "test", now)
        game.tick(SERVER_DT, now=now + 2.4)

        self.assertFalse(player["dead"])
        self.assertEqual(player["lives"], PLAYER_STAGE_LIVES)
        self.assertTrue(any(ev == "stage_failed" for ev, _ in events))
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_abandon_stage_restart_resets_current_stage_from_room(self):
        game, events = self.make_game()
        now = game._now()
        game.add_player("p2")
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        player["materials"] = 7
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        scene_id = player["scene"]
        self.assertTrue(scene_id.startswith("room:"))
        player["paused"] = True
        game.players["p2"]["paused"] = True

        exit_point = {
            "id": "partial-exit",
            "type": "service",
            "name": "维修通道",
            "text": "半途撤离",
            "requires": {},
            "x": player.get("main_x", 1000),
            "y": player.get("main_y", 1000),
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.62,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#66d9ff",
        }
        game.extractions = [exit_point]
        game.mission = exit_point
        game.spawn_zombie(x=player["x"] + 140, y=player["y"], ztype="runner", scene=scene_id)
        game.spawn_item(x=player["x"], y=player["y"], item_type="parts", scene=scene_id)
        game.task_counts["fuse"] = 2
        old_wave = game.wave

        self.assertTrue(game.restart_current_stage("p1", reason="abandon"))

        self.assertEqual(game.wave, old_wave)
        self.assertEqual(player["scene"], "main")
        self.assertEqual(player["lives"], PLAYER_STAGE_LIVES)
        self.assertEqual(player["materials"], 7)
        self.assertFalse(player["paused"])
        self.assertFalse(game.players["p2"]["paused"])
        self.assertEqual(game.task_counts["fuse"], 0)
        self.assertTrue(game.extractions)
        self.assertTrue(all(exit_data.get("charge", 0) == 0 for exit_data in game.extractions))
        self.assertIsNot(game.extractions[0], exit_point)
        self.assertFalse(any(zombie.get("scene") == scene_id for zombie in game.zombies.values()))
        self.assertFalse(any(item.get("scene") == scene_id for item in game.items.values()))
        failed = [data for ev, data in events if ev == "stage_failed"][-1]
        self.assertEqual(failed["reason"], "abandon")
        self.assertEqual(failed["scene"], "main")
        self.assertIn("mw", failed)
        self.assertTrue(any(ev == "scene_change" and data["reason"] == "respawn" for ev, data in events))
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_abandon_stage_during_partial_extraction_charge_resets_lifecycle(self):
        game, events = self.make_game()
        now = game._now()
        player = game.players["p1"]
        exit_point = {
            "id": "mid-charge",
            "type": "service",
            "name": "维修通道",
            "text": "半途撤离",
            "requires": {},
            "x": player["x"],
            "y": player["y"],
            "radius": MISSION_CAPTURE_RADIUS,
            "charge": 0.0,
            "visible": True,
            "done": False,
            "wave": game.wave,
            "color": "#66d9ff",
        }
        game.extractions = [exit_point]
        game.mission = exit_point

        game._update_mission(EXTRACTION_CAPTURE_SECONDS * 0.42, now)
        self.assertGreater(exit_point["charge"], 0.35)
        self.assertLess(exit_point["charge"], 1)

        self.assertTrue(game.restart_current_stage("p1", reason="abandon"))

        self.assertIsNone(game.intermission)
        self.assertTrue(game.extractions)
        self.assertTrue(all(exit_data.get("charge", 0) == 0 for exit_data in game.extractions))
        failed = [data for ev, data in events if ev == "stage_failed"][-1]
        self.assertEqual(failed["reason"], "abandon")
        self.assertEqual(failed["sceneId"], "main")
        self.assertTrue(any(ev == "wave_start" for ev, _ in events))

    def test_abandon_stage_restart_is_denied_during_intermission(self):
        game, events = self.make_game()
        game.intermission = {"ready": [], "players": ["p1"], "nextWave": game.wave + 1}

        self.assertFalse(game.restart_current_stage("p1", reason="abandon"))

        self.assertIsNotNone(game.intermission)
        denied = [data for ev, data in events if ev == "stage_restart_denied"]
        self.assertEqual(len(denied), 1)
        self.assertIn("整备中", denied[0]["reason"])

    def test_stage_failure_reason_must_be_explicit(self):
        game, _ = self.make_game()
        game.intermission = {"ready": ["p1"], "players": ["p1"]}
        game.zombies[99] = self.zombie(99, 1200, 1200)
        old_intermission = game.intermission
        old_zombies = dict(game.zombies)

        with self.assertRaises(ValueError):
            game.restart_current_stage("p1", reason="manual")

        self.assertIs(game.intermission, old_intermission)
        self.assertEqual(game.zombies, old_zombies)

    def test_interact_input_clears_while_dead_or_in_intermission(self):
        game, _ = self.make_game()
        player = game.players["p1"]
        game.intermission = {"ready": [], "players": ["p1"]}

        game.handle_input("p1", {
            "seq": 1,
            "keys": {"right": True},
            "interact": True,
            "shooting": True,
        })

        self.assertEqual(player["keys"], {})
        self.assertFalse(player["shooting"])
        self.assertFalse(player["interact_requested"])

        game.intermission = None
        player["dead"] = True
        game.handle_input("p1", {
            "seq": 2,
            "keys": {"right": True},
            "interact": True,
            "shooting": True,
        })

        self.assertEqual(player["keys"], {})
        self.assertFalse(player["shooting"])
        self.assertFalse(player["interact_requested"])

    def test_disconnect_inside_room_sweeps_room_entities(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("kind") == "room")
        player = game.players["p1"]
        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now)
        scene_id = player["scene"]
        self.assertTrue(scene_id.startswith("room:"))

        zid = game.spawn_zombie(x=player["x"] + 130, y=player["y"], ztype="runner", scene=scene_id)
        iid = game.spawn_item(x=player["x"], y=player["y"], item_type="parts", scene=scene_id)
        game.bullets["room-bullet"] = {"owner": "p1", "scene": scene_id, "x": player["x"], "y": player["y"]}

        self.assertTrue(game.remove_player("p1"))

        self.assertNotIn(zid, game.zombies)
        self.assertNotIn(iid, game.items)
        self.assertNotIn("room-bullet", game.bullets)

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
        game.wave_kills = 999

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
        game.wave_kills = 999

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
        player["combo"] = 7
        player["combo_until"] = now + 2

        game._gain_score("p1", 12, 8, now)

        self.assertEqual(player["combo"], 8)
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

        self.assertGreater(game._pending_fog_spawn_count(), 0)
        game._process_pending_fog_spawns(now)
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
        self.assertEqual(source_events[-1]["sceneId"], "main")
        self.assertGreater(source_events[-1]["sourceCount"], 0)
        while game._pending_fog_spawn_count():
            game._process_pending_fog_spawns(now)
        self.assertTrue(any(zombie.get("source") == "infection" for zombie in game.zombies.values()))

    def test_main_fog_wave_still_consumes_global_wave_budget(self):
        game, _ = self.make_game()
        now = game._now()
        game.zombies.clear()
        game.wave_remaining = 20
        game.infection_source_remaining = 0

        queued = game._trigger_fog_wave(now, reason="silence", force=True)

        self.assertGreater(queued, 0)
        self.assertEqual(game.wave_remaining, 20 - queued)
        self.assertTrue(all(entry.get("source") == "wave" for entry in game.pending_fog_spawns))

    def test_fog_wave_does_not_emit_per_zombie_spawn_burst(self):
        game, events = self.make_game()
        now = game._now()
        game.zombies.clear()
        game.wave_remaining = 40
        game.infection_source_remaining = 0

        spawned = game._trigger_fog_wave(now, reason="silence", force=True)

        self.assertGreater(spawned, 0)
        self.assertEqual(len(game.zombies), 0)
        self.assertEqual(game._pending_fog_spawn_count(), spawned)
        self.assertTrue(any(ev == "fog_wave" for ev, _ in events))
        self.assertFalse(any(ev == "z_spawn" for ev, _ in events))

    def test_fog_wave_spawns_are_deferred_over_multiple_ticks(self):
        game, events = self.make_game()
        now = game._now()
        game.wave = 3
        game.zombies.clear()
        game.wave_remaining = 80
        game.infection_source_remaining = 0

        queued = game._trigger_fog_wave(now, reason="silence", force=True)

        self.assertGreater(queued, FOG_SPAWNS_PER_TICK)
        self.assertEqual(len(game.zombies), 0)
        self.assertEqual(game._pending_fog_spawn_count(), queued)
        self.assertEqual(game._process_pending_fog_spawns(now), FOG_SPAWNS_PER_TICK)
        self.assertEqual(len(game.zombies), FOG_SPAWNS_PER_TICK)
        self.assertEqual(game._pending_fog_spawn_count(), queued - FOG_SPAWNS_PER_TICK)
        self.assertFalse(any(ev == "z_spawn" for ev, _ in events))

    def test_indoor_fog_wave_is_capped_and_dripped_slowly(self):
        game, events = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.wave = 5
        game.zombies.clear()
        game.wave_remaining = 80
        game.infection_source_remaining = 40
        game.pending_fog_spawns.clear()
        events.clear()

        queued = game._trigger_fog_wave(now + 1.0, reason="lab", force=True, origin=player)

        self.assertGreater(queued, 0)
        self.assertLessEqual(queued, ROOM_FOG_WAVE_MAX)
        self.assertEqual(game._pending_fog_spawn_count(), queued)
        fog_events = [data for ev, data in events if ev == "fog_wave"]
        self.assertTrue(fog_events)
        self.assertEqual(fog_events[-1]["sceneId"], scene_id)
        self.assertEqual(game._process_pending_fog_spawns(now + 1.1), ROOM_FOG_SPAWNS_PER_TICK)
        self.assertEqual(len(game.zombies), ROOM_FOG_SPAWNS_PER_TICK)
        self.assertEqual(game._pending_fog_spawn_count(), queued - ROOM_FOG_SPAWNS_PER_TICK)

    def test_room_entry_wave_is_independent_from_global_budget(self):
        game, events = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "armory")
        game.zombies.clear()
        game.pending_fog_spawns.clear()
        game.wave_remaining = 0
        game.infection_source_remaining = 0
        events.clear()

        player = self.enter_room(game, room, now)
        queued = game._pending_fog_spawn_count()

        self.assertGreater(queued, 0)
        self.assertEqual(game.wave_remaining, 0)
        self.assertEqual(game.infection_source_remaining, 0)
        self.assertEqual(len(game.zombies), 0)
        self.assertTrue(any(ev == "fog_wave" and data["sceneId"] == player["scene"] for ev, data in events))
        while game._pending_fog_spawn_count():
            game._process_pending_fog_spawns(now + 1.0)
        self.assertTrue(any(zombie.get("source") == "room" for zombie in game.zombies.values()))

    def test_room_entry_wave_resets_when_stage_map_is_regenerated(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        old_scene_id = player["scene"]

        self.assertTrue(game.room_scenes[old_scene_id].get("entry_wave_spawned"))

        game._gen_obstacles()

        self.assertTrue(game.room_scenes)
        self.assertFalse(any(scene.get("entry_wave_spawned") for scene in game.room_scenes.values()))

    def test_indoor_fog_wave_does_not_advance_main_fog_timers(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        game.zombies.clear()
        game.wave_remaining = 80
        game.infection_source_remaining = 40
        game.pending_fog_spawns.clear()
        game.next_fog_wave_at = now + 123
        game.fog_active_until = now + 77

        queued = game._trigger_fog_wave(now + 1.0, reason="lab", force=True, origin=player)

        self.assertGreater(queued, 0)
        self.assertEqual(game.next_fog_wave_at, now + 123)
        self.assertEqual(game.fog_active_until, now + 77)

    def test_mixed_fog_queue_uses_scene_specific_spawn_budgets(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.zombies.clear()
        game.pending_fog_spawns = [
            {"scene": scene_id, "ztype": "runner", "spawn_index": 0},
            {"scene": scene_id, "ztype": "runner", "spawn_index": 1},
            {"scene": SCENE_MAIN, "ztype": "shade"},
            {"scene": SCENE_MAIN, "ztype": "shade"},
            {"scene": SCENE_MAIN, "ztype": "shade"},
            {"scene": SCENE_MAIN, "ztype": "shade"},
        ]

        spawned = game._process_pending_fog_spawns(now + 1.0)

        self.assertEqual(spawned, FOG_SPAWNS_PER_TICK + ROOM_FOG_SPAWNS_PER_TICK)
        self.assertEqual(
            sum(1 for zombie in game.zombies.values() if zombie.get("scene") == scene_id),
            ROOM_FOG_SPAWNS_PER_TICK,
        )
        self.assertEqual(
            sum(1 for zombie in game.zombies.values() if zombie.get("scene") == SCENE_MAIN),
            FOG_SPAWNS_PER_TICK,
        )
        self.assertEqual(
            [entry.get("scene") for entry in game.pending_fog_spawns],
            [SCENE_MAIN],
        )

    def test_mixed_fog_queue_allows_independent_room_budgets(self):
        game, _ = self.make_game()
        now = game._now()
        scene_a, scene_b = list(game.room_scenes.keys())[:2]
        game.zombies.clear()
        game.pending_fog_spawns = [
            {"scene": scene_a, "ztype": "runner", "spawn_index": 0},
            {"scene": scene_a, "ztype": "runner", "spawn_index": 1},
            {"scene": scene_b, "ztype": "crawler", "spawn_index": 0},
            {"scene": scene_b, "ztype": "crawler", "spawn_index": 1},
            {"scene": SCENE_MAIN, "ztype": "shade"},
            {"scene": SCENE_MAIN, "ztype": "shade"},
            {"scene": SCENE_MAIN, "ztype": "shade"},
            {"scene": SCENE_MAIN, "ztype": "shade"},
        ]

        spawned = game._process_pending_fog_spawns(now + 1.0)

        self.assertEqual(spawned, FOG_SPAWNS_PER_TICK + ROOM_FOG_SPAWNS_PER_TICK * 2)
        self.assertEqual(
            sum(1 for zombie in game.zombies.values() if zombie.get("scene") == scene_a),
            ROOM_FOG_SPAWNS_PER_TICK,
        )
        self.assertEqual(
            sum(1 for zombie in game.zombies.values() if zombie.get("scene") == scene_b),
            ROOM_FOG_SPAWNS_PER_TICK,
        )
        self.assertEqual(
            sum(1 for zombie in game.zombies.values() if zombie.get("scene") == SCENE_MAIN),
            FOG_SPAWNS_PER_TICK,
        )

    def test_room_reentry_after_sweep_drops_stale_fog_queue(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.pending_fog_spawns = [
            {"scene": scene_id, "ztype": "runner", "spawn_index": 0},
            {"scene": SCENE_MAIN, "ztype": "shade"},
        ]
        game.zombies[99] = self.zombie(99, 520, 520, ztype="runner")
        game.zombies[99]["scene"] = scene_id

        self.assertTrue(game._leave_room_scene("p1", player, now + 1.0))

        self.assertEqual([entry.get("scene") for entry in game.pending_fog_spawns], [SCENE_MAIN])
        self.assertFalse(any(zombie.get("scene") == scene_id for zombie in game.zombies.values()))

        player["x"] = room["x"] + room["w"] / 2
        player["y"] = room["y"] + room["h"] / 2
        game.handle_input("p1", {"seq": player.get("ack_seq", 0) + 1, "interact": True})
        game._apply_facility_effects(SERVER_DT, now + 3.0)

        self.assertEqual(player["scene"], scene_id)
        self.assertEqual([entry.get("scene") for entry in game.pending_fog_spawns], [SCENE_MAIN])

    def test_entering_danger_room_queues_one_independent_wave(self):
        game, events = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)

        self.assertEqual(len(game.zombies), 0)
        self.assertGreater(game._pending_fog_spawn_count(), 0)
        first_queue = game._pending_fog_spawn_count()
        self.assertTrue(any(ev == "fog_wave" and data["sceneId"] == player["scene"] for ev, data in events))

        game._apply_facility_effects(SERVER_DT, now + SERVER_DT)

        self.assertEqual(len(game.zombies), 0)
        self.assertEqual(game._pending_fog_spawn_count(), first_queue)
        self.assertTrue(any(ev == "lab_reactor" for ev, _ in events))

    def test_indoor_fog_spawns_rotate_room_entry_points(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        scene = game.room_scenes[scene_id]
        game.zombies.clear()
        game.wave_remaining = 80
        game.infection_source_remaining = 40
        game.pending_fog_spawns.clear()

        queued = game._trigger_fog_wave(now + 1.0, reason="lab", force=True, origin=player)
        while game._pending_fog_spawn_count():
            game._process_pending_fog_spawns(now + 1.2)

        self.assertGreaterEqual(queued, 3)
        spawned = list(game.zombies.values())
        self.assertEqual(len(spawned), queued)
        expected_points = scene["zombie_points"][: min(3, len(scene["zombie_points"]))]
        for zombie, point in zip(spawned[:3], expected_points):
            self.assertLess(math.hypot(zombie["x"] - point[0], zombie["y"] - point[1]), 120)
            self.assertGreaterEqual(math.hypot(zombie["x"] - player["x"], zombie["y"] - player["y"]), 240)

    def test_room_pending_fog_spawn_prewarms_nav_before_movement(self):
        game, _ = self.make_game()
        now = game._now()
        room = next(feature for feature in game.map_features if feature.get("effect") == "lab")
        player = self.enter_room(game, room, now)
        scene_id = player["scene"]
        game.room_nav_cache.clear()
        self.assertGreater(game._pending_fog_spawn_count(), 0)

        game._process_pending_fog_spawns(now + SERVER_DT)

        self.assertTrue(any(key[0] == scene_id for key in game.room_nav_cache))
        self.assertTrue(any(zombie.get("scene") == scene_id for zombie in game.zombies.values()))

    def test_pending_fog_spawns_clear_with_empty_room_scene(self):
        game, _ = self.make_game()
        game.pending_fog_spawns = [
            {"scene": "room:a"},
            {"scene": SCENE_MAIN},
            {"scene": "room:b"},
        ]

        game._sweep_empty_room_scene("room:a")

        self.assertEqual([entry["scene"] for entry in game.pending_fog_spawns], [SCENE_MAIN, "room:b"])

    def test_wave_maintenance_pauses_while_fog_queue_materializes(self):
        game, _ = self.make_game()
        now = game._now()
        game.zombies.clear()
        game.wave_remaining = 80
        game.zombie_spawn_timer = 999
        game.pending_fog_spawns = [{"scene": SCENE_MAIN}]

        game._maintain_zombies(10.0, now)

        self.assertEqual(len(game.zombies), 0)
        self.assertEqual(game.wave_remaining, 80)

    def test_wave_maintenance_does_not_spawn_main_zombies_for_indoor_only_players(self):
        game, _ = self.make_game()
        now = game._now()
        player = game.players["p1"]
        player["scene"] = "room:test"
        game.zombies.clear()
        game.wave_remaining = 80
        game.zombie_spawn_timer = 999

        game._maintain_zombies(10.0, now)

        self.assertEqual(len(game.zombies), 0)
        self.assertEqual(game.wave_remaining, 80)

    def test_pressure_pack_uses_snapshot_sync_not_spawn_burst(self):
        game, events = self.make_game()
        now = game._now()
        game.zombies.clear()
        game.wave_remaining = 20

        spawned = game._spawn_pressure_pack(6, now, urgent=True)

        self.assertGreater(spawned, 0)
        self.assertFalse(any(ev == "z_spawn" for ev, _ in events))

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
