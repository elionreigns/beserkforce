import tempfile
import unittest
from pathlib import Path

from beserkforce.core import Runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_bootstrap_uses_five_flight_roles(self):
        self.assertEqual({job["producerRoleId"] for job in self.runtime.jobs()}, {50, 51, 52, 53, 54})
        self.assertEqual(len(self.runtime.roles()), 5)

    def test_claim_has_single_writer_lease(self):
        first = self.runtime.claim_job("BF-HELI-50", "agent-a")
        self.assertEqual(first["state"], "claimed")
        with self.assertRaisesRegex(ValueError, "leased by agent-a"):
            self.runtime.claim_job("BF-HELI-50", "agent-b")

    def test_exact_action_hash_protects_approval(self):
        approval = self.runtime.request_approval("BF-HELI-53", "outreach", "public traveler", "Send exact helpful reply", "$0", "Could be perceived as spam")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.runtime.decide_approval(approval["approvalId"], "approved", "Eric", "wrong")
        decided = self.runtime.decide_approval(approval["approvalId"], "approved", "Eric", approval["actionHash"])
        self.assertEqual(decided["status"], "approved")

    def test_sale_requires_three_verified_proof_types(self):
        self.runtime.add_evidence("BF-HELI-50", "booking-record", "test", "booking proof", True)
        with self.assertRaisesRegex(ValueError, "attribution"):
            self.runtime.verify_helicopter_sale("BF-HELI-50", "Eric", "BOOK-1")

    def test_safety_demo_closes_with_hashed_artifact(self):
        result = self.runtime.run_safety_demo()
        job = next(item for item in self.runtime.jobs() if item["jobId"] == result["jobId"])
        self.assertEqual(job["state"], "closed")
        self.assertEqual(len(result["sha256"]), 64)

    def test_codex_is_primary_bounded_brain(self):
        plan = self.runtime.brain_plan("BF-HELI-50")
        self.assertEqual(plan["brain"]["role"], "primary conductor brain")
        self.assertIn("workspace-write", plan["command"])
        self.assertNotIn("danger-full-access", plan["command"])

    def test_opencode_is_secondary_bounded_brain(self):
        plan = self.runtime.brain_plan("BF-HELI-50", engine="opencode")
        self.assertEqual(plan["engine"], "opencode")
        self.assertEqual(plan["brain"]["role"], "secondary conductor brain")
        self.assertIn("run", plan["command"])
        self.assertIn("--auto", plan["command"])
        self.assertNotIn("danger-full-access", plan["command"])

    def test_brains_registry_exposes_codex_opencode_and_grok(self):
        engines = {brain["engine"] for brain in self.runtime.brains_status()}
        self.assertEqual(engines, {"codex", "opencode", "grok"})
        self.assertEqual(self.runtime.brain.identity()["role"], "primary conductor brain")

    def test_grok_cli_is_a_bounded_brain(self):
        plan = self.runtime.brain_plan("BF-HELI-50", engine="grok")
        self.assertEqual(plan["engine"], "grok")
        self.assertEqual(plan["brain"]["model"], "grok-4.7")
        self.assertIn("--prompt-file", plan["command"])
        self.assertIn("bypassPermissions", plan["command"])
        self.assertIn("grok-4.7", plan["command"])
        self.assertNotIn("danger-full-access", plan["command"])

    def test_unknown_engine_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown brain engine"):
            self.runtime.brain_plan("BF-HELI-50", engine="not-a-brain")

    def test_chat_requires_a_message(self):
        with self.assertRaisesRegex(ValueError, "Chat message is required"):
            self.runtime.chat("   ", engine="opencode")

    def test_chat_rejects_unknown_engine_before_running(self):
        with self.assertRaisesRegex(ValueError, "Unknown brain engine"):
            self.runtime.chat("hello", engine="not-a-brain")

    def test_json_extraction_reads_last_object(self):
        from beserkforce.brain import extract_json_object
        text = 'thinking...\n{"jobId": "A", "summary": "one"}\nnoise\n{"jobId": "B", "summary": "two", "nested": {"x": 1}}'
        parsed = extract_json_object(text)
        self.assertEqual(parsed["jobId"], "B")
        self.assertEqual(parsed["nested"], {"x": 1})

    def test_reasoning_tags_are_stripped_from_replies(self):
        from beserkforce.brain import clean_reply, opencode_text
        self.assertEqual(clean_reply("thinking\nBeserkForce is a runtime."), "BeserkForce is a runtime.")
        self.assertEqual(clean_reply("<thinking>secret</thinking>\nAnswer here."), "Answer here.")
        self.assertEqual(clean_reply("React\n\n\n\nNow the real answer."), "React\n\nNow the real answer.")
        stdout = "\n".join([
            '{"type":"reasoning","part":{"type":"reasoning","text":"internal chain"}}',
            '{"type":"text","part":{"type":"text","text":"thinking"}}',
            '{"type":"step_finish","part":{"type":"step-finish","reason":"stop"}}',
            '{"type":"text","part":{"type":"text","text":"BeserkForce gates external actions."}}',
            "not json",
        ])
        self.assertEqual(opencode_text(stdout), "BeserkForce gates external actions.")


if __name__ == "__main__":
    unittest.main()
