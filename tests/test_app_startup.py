import unittest
import asyncio
from pathlib import Path


class AppStartupTest(unittest.TestCase):
    def test_import_does_not_start_background_tasks(self):
        import server_asgi

        self.assertFalse(server_asgi._tasks_started)

    def test_socketio_uses_websocket_transport_for_lan_play(self):
        import server_asgi

        self.assertEqual(server_asgi.sio.async_mode, "asgi")
        self.assertEqual(server_asgi.sio.eio.transports, ["websocket"])
        self.assertEqual(server_asgi.sio.eio.ping_interval, 5)
        self.assertEqual(server_asgi.sio.eio.ping_timeout, 10)
        self.assertFalse(server_asgi._tasks_started)

    def test_frontend_uses_local_socketio_client_for_lan_play(self):
        root = Path(__file__).resolve().parents[1]
        template = (root / "templates" / "index.html").read_text(encoding="utf-8")
        vendor = root / "static" / "vendor" / "socket.io.min.js"

        self.assertNotIn("cdn.socket.io", template)
        self.assertIn("vendor/socket.io.min.js", template)
        self.assertTrue(vendor.exists())
        self.assertGreater(vendor.stat().st_size, 40000)

    def test_background_tasks_start_once_under_concurrency(self):
        import server_asgi

        calls = []
        original = server_asgi.sio.start_background_task
        server_asgi._tasks_started = False

        def fake_start(fn):
            calls.append(fn.__name__)

        async def start_many():
            await asyncio.gather(*(server_asgi.start_background_tasks() for _ in range(12)))

        server_asgi.sio.start_background_task = fake_start
        try:
            asyncio.run(start_many())
        finally:
            server_asgi.sio.start_background_task = original
            server_asgi._tasks_started = False

        self.assertEqual(calls.count("logic_loop"), 1)
        self.assertEqual(calls.count("sync_loop"), 1)
        self.assertEqual(len(calls), 2)


if __name__ == "__main__":
    unittest.main()
