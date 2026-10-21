"""有界并发消费者：CONSUMER_WORKERS 控制启动线程数，且每个 worker 独立 runner。"""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.main import _consumer_worker_count, start_consumer


class ConsumerWorkerCountTest(unittest.TestCase):
    def test_default_is_one(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CONSUMER_WORKERS", None)
            self.assertEqual(_consumer_worker_count(), 1)

    def test_configured_value_is_bounded(self):
        for value, expected in (("4", 4), ("0", 1), ("-3", 1), ("999", 16), ("abc", 1)):
            with patch.dict(os.environ, {"CONSUMER_WORKERS": value}, clear=False):
                self.assertEqual(_consumer_worker_count(), expected)

    def test_start_consumer_starts_configured_workers(self):
        with patch.dict(os.environ, {"AUTO_CONSUME": "true", "CONSUMER_WORKERS": "3"},
                        clear=False), \
                patch("app.main._build_runner", return_value=object()) as build_runner, \
                patch("app.main.threading.Thread") as thread_cls, \
                patch("app.main.consumer_loop"):
            start_consumer()

        self.assertEqual(build_runner.call_count, 3)
        self.assertEqual(thread_cls.call_count, 3)
        for call in thread_cls.call_args_list:
            self.assertTrue(call.kwargs.get("daemon"))
        self.assertEqual(thread_cls.return_value.start.call_count, 3)

    def test_auto_consume_false_starts_no_workers(self):
        with patch.dict(os.environ, {"AUTO_CONSUME": "false", "CONSUMER_WORKERS": "3"},
                        clear=False), \
                patch("app.main._build_runner") as build_runner, \
                patch("app.main.threading.Thread") as thread_cls:
            start_consumer()

        build_runner.assert_not_called()
        thread_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
