import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("beserk_app", ROOT / "app.py")
APP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(APP)


class SkeletonTests(unittest.TestCase):
    def test_health_is_honest_and_online(self):
        state = APP.health()
        self.assertTrue(state["ok"])
        self.assertEqual(state["stage"], "nerves-online")
        self.assertIn("approval", state["authority"])

    def test_original_workforce_is_parent(self):
        role_registry = (ROOT / APP.CONFIG["roleRegistry"]).resolve()
        self.assertTrue(role_registry.is_file())
        self.assertNotIn(str(ROOT.resolve()), str(role_registry))

    def test_launch_is_a_window_not_a_browser_port(self):
        launcher = (ROOT / "Start-BeserkForce.ps1").read_text(encoding="utf-8")
        self.assertIn("BeserkForce.pyw", launcher)
        self.assertNotIn("Start-Process 'http://127.0.0.1:8877'", launcher)
        self.assertTrue((ROOT / "BeserkForce.pyw").is_file())


if __name__ == "__main__":
    unittest.main()
