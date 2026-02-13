"""Contract test for TokenCounterPort implementations (T072)."""

from __future__ import annotations

from courseflow.domain.ports import TokenCounterPort
from courseflow.infrastructure.token_counting.tiktoken_counter import TiktokenCounter


def _assert_token_counter_contract(counter: TokenCounterPort) -> None:
    assert hasattr(counter, "count_tokens")
    assert callable(counter.count_tokens)
    count = counter.count_tokens("hello world")
    assert isinstance(count, int)
    assert count > 0


def test_tiktoken_counter_implements_token_counter_port_contract():
    counter = TiktokenCounter()
    _assert_token_counter_contract(counter)
