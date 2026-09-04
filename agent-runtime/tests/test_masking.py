import unittest

from app.masking import mask_sensitive


class MaskingTest(unittest.TestCase):
    def test_masks_api_key(self):
        masked = mask_sensitive("api_key=sk-1234567890")
        self.assertNotIn("sk-1234567890", masked)
        self.assertIn("ap***", masked)

    def test_masks_password(self):
        masked = mask_sensitive("password=secret123")
        self.assertNotIn("secret123", masked)

    def test_masks_token(self):
        masked = mask_sensitive("Authorization: Bearer abcdef")
        self.assertNotIn("abcdef", masked)

    def test_keeps_normal_text(self):
        text = "service=payment latency=100"
        self.assertEqual(mask_sensitive(text), text)


if __name__ == "__main__":
    unittest.main()