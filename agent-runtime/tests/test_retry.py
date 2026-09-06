import unittest

import httpx
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


def _http_status_error(status: int, retry_after: str | None = None) -> Exception:
    """构造 httpx.HTTPStatusError（P1-AR-04 语义断言用）。"""
    headers = {"Retry-After": retry_after} if retry_after else {}
    request = httpx.Request("POST", "https://llm.example/v1/chat/completions")
    response = httpx.Response(status, headers=headers, request=request)
    return httpx.HTTPStatusError(f"{status}", request=request, response=response)


class StatusAwareRetryTest(unittest.TestCase):
    def test_429_honors_retry_after_header(self):
        calls = {"n": 0}

        class RateLimited(LLMProvider):
            def complete(self, messages, tools=None):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise _http_status_error(429, "0")
                return LLMResult("ok")

        result = RetryLLMProvider(RateLimited(), max_retries=1).complete(
            [Message(role="user", content="hi")])
        self.assertEqual(result.content, "ok")
        self.assertEqual(calls["n"], 2)

    def test_429_with_long_retry_after_gives_up_waiting(self):
        # Retry-After 超上限（预算型诊断等不起）：不再等待，直接上抛
        class SlowRateLimit(LLMProvider):
            def __init__(self):
                self.calls = 0

            def complete(self, messages, tools=None):
                self.calls += 1
                raise _http_status_error(429, "600")

        inner = SlowRateLimit()
        with self.assertRaises(httpx.HTTPStatusError):
            RetryLLMProvider(inner, max_retries=2, delay_seconds=0.01).complete(
                [Message(role="user", content="hi")])
        self.assertEqual(inner.calls, 1)

    def test_4xx_is_not_retried(self):
        calls = {"n": 0}

        class AuthError(LLMProvider):
            def complete(self, messages, tools=None):
                calls["n"] += 1
                raise _http_status_error(401)

        with self.assertRaises(httpx.HTTPStatusError):
            RetryLLMProvider(AuthError(), max_retries=2, delay_seconds=0.01).complete(
                [Message(role="user", content="hi")])
        self.assertEqual(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
