import unittest

from app.llm.base import LLMProvider, Message
from app.llm.retry import RetryLLMProvider
from app.models import LLMResult


class FlakyLLM(LLMProvider):
    def __init__(self, fail_times: int = 1):
        self.fail_times = fail_times
        self.calls = 0

    def complete(self, messages, tools=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("temporary failure")
        return LLMResult("ok")


class RetryLLMTest(unittest.TestCase):
    def test_retry_succeeds_after_transient_failure(self):
        inner = FlakyLLM(fail_times=1)
        provider = RetryLLMProvider(inner, max_retries=2)
        result = provider.complete([Message(role="user", content="hi")])
        self.assertEqual(result.content, "ok")
        self.assertEqual(inner.calls, 2)

    def test_retry_gives_up_after_max_retries(self):
        inner = FlakyLLM(fail_times=10)
        provider = RetryLLMProvider(inner, max_retries=2)
        with self.assertRaises(RuntimeError):
            provider.complete([Message(role="user", content="hi")])
        self.assertEqual(inner.calls, 3)


if __name__ == "__main__":
    unittest.main()
