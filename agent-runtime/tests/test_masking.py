import unittest

from app.masking import mask_dict, mask_sensitive


class MaskingTest(unittest.TestCase):
    def test_masks_api_key_value(self):
        masked = mask_sensitive("api_key=sk-1234567890")
        self.assertNotIn("sk-1234567890", masked)
        # 掩的是「值」，key 名保留（便于排障时知道是哪个字段）
        self.assertIn("api_key=", masked)
        self.assertIn("sk-1***", masked)

    def test_masks_password_value(self):
        masked = mask_sensitive("password=secret123")
        self.assertNotIn("secret123", masked)
        self.assertIn("password=", masked)

    def test_masks_bearer_token(self):
        masked = mask_sensitive("Authorization: Bearer abcdef123456")
        self.assertNotIn("abcdef123456", masked)
        self.assertIn("Bearer", masked)

    def test_masks_bare_sk_token(self):
        masked = mask_sensitive("read the key sk-abcdefghijklmnop from vault")
        self.assertNotIn("sk-abcdefghijklmnop", masked)

    def test_keeps_normal_text(self):
        text = "service=payment latency=100"
        self.assertEqual(mask_sensitive(text), text)

    def test_key_name_not_mistaken_for_secret(self):
        """回归：旧实现掩的是 key 名（api_key → ap***），密钥值原样保留。"""
        masked = mask_sensitive("api_key=supersecretvalue")
        self.assertNotIn("ap***", masked)
        self.assertNotIn("supersecretvalue", masked)

    def test_mask_dict_recurses(self):
        out = mask_dict({"a": "token=abcd1234", "b": ["password=pw123456"], "c": 7})
        self.assertNotIn("abcd1234", str(out))
        self.assertNotIn("pw123456", str(out))
        self.assertEqual(out["c"], 7)


if __name__ == "__main__":
    unittest.main()
