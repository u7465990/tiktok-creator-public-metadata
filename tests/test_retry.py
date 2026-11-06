import unittest

from collector.fetch import is_transient
from collector.types import Snapshot


def snap(status: int) -> Snapshot:
    return Snapshot(url="https://example.invalid", status=status,
                    body="", fetched_at="2026-11-06T00:00:00Z")


class TestRetryPolicy(unittest.TestCase):
    def test_transport_failure_is_retried(self):
        self.assertTrue(is_transient(snap(0)))

    def test_rate_limit_and_5xx_are_retried(self):
        self.assertTrue(is_transient(snap(429)))
        self.assertTrue(is_transient(snap(500)))
        self.assertTrue(is_transient(snap(503)))

    def test_explicit_refusal_is_not_retried(self):
        # 403 是对方明确拒绝，重试只会让 IP 更糟
        self.assertFalse(is_transient(snap(403)))

    def test_deterministic_outcomes_are_not_retried(self):
        self.assertFalse(is_transient(snap(404)))
        self.assertFalse(is_transient(snap(200)))


if __name__ == "__main__":
    unittest.main()
