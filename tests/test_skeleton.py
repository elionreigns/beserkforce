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


if __name__ == "__main__":
    unittest.main()
