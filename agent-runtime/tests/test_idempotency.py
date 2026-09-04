import shutil
import unittest
from pathlib import Path

from app.idempotency import FileIdempotencyStore


class IdempotencyStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(__file__).resolve().parent / ".tmp_idem"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_duplicate_event_is_skipped(self):
        store = FileIdempotencyStore(self.tmp, ttl_seconds=60)
        self.assertFalse(store.is_processed("event-1"))
        store.mark_processed("event-1")
        self.assertTrue(store.is_processed("event-1"))

    def test_expired_event_is_reprocessed(self):
        store = FileIdempotencyStore(self.tmp, ttl_seconds=0)
        store.mark_processed("event-1")
        self.assertFalse(store.is_processed("event-1"))


if __name__ == "__main__":
    unittest.main()