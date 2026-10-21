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

    def test_unknown_action_fails_closed_to_high_risk(self):
        # 与 CP 的 RiskPolicy 同语义：未知动作不能默认放行。
        self.assertEqual(classify("some_new_action"), RiskLevel.HIGH_RISK)
        self.assertTrue(requires_approval("some_new_action"))

    def test_none_is_treated_as_high_risk(self):
        self.assertTrue(requires_approval(None))


if __name__ == "__main__":
    unittest.main()
