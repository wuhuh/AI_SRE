import unittest

from app.tools.policy import assert_database_allowed, assert_namespace_allowed, assert_service_allowed


class ToolPolicyTest(unittest.TestCase):
    def test_allows_known_namespace(self):
        assert_namespace_allowed("default")

    def test_rejects_unknown_namespace(self):
        with self.assertRaises(PermissionError):
            assert_namespace_allowed("evil-namespace")

    def test_allows_known_database(self):
        assert_database_allowed("aisre")

    def test_rejects_unknown_database(self):
        with self.assertRaises(PermissionError):
            assert_database_allowed("admin")

    def test_allows_known_service(self):
        assert_service_allowed("payment-service")

    def test_rejects_unknown_service(self):
        with self.assertRaises(PermissionError):
            assert_service_allowed("unknown-service")


if __name__ == "__main__":
    unittest.main()