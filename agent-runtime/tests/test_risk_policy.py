import unittest

from app.risk_policy import RiskLevel, classify, requires_approval


class RiskPolicyTest(unittest.TestCase):
    def test_high_risk_actions_require_approval(self):
        self.assertTrue(requires_approval("scale_deployment"))
        self.assertTrue(requires_approval("delete_pod"))
        self.assertTrue(requires_approval("rollback_deployment"))

    def test_low_risk_actions_do_not_require_approval(self):
        self.assertFalse(requires_approval("restart_pod"))
        self.assertFalse(requires_approval("disable_fault"))
        self.assertFalse(requires_approval("clear_redis_cache"))

    def test_unknown_action_defaults_to_low_risk(self):
        self.assertEqual(classify("some_new_action"), RiskLevel.LOW_RISK)

    def test_none_is_treated_as_high_risk(self):
        self.assertTrue(requires_approval(None))


if __name__ == "__main__":
    unittest.main()