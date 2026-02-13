"""Unit tests for conversation domain entities.

Tests cover:
- Conversation creation and validation
- ConversationTurn validation (role, content, token count)
- TurnHistory token budget enforcement and trimming
- TurnHistory immutability and LLM context formatting
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from courseflow.domain.models import Conversation, ConversationTurn, TurnHistory


class TestConversation:
    """Test suite for Conversation aggregate root."""

    def test_create_new_conversation(self) -> None:
        """Test creating new conversation with UUID and timestamp."""
        conv = Conversation(id=uuid4())
        assert conv.id is not None
        assert isinstance(conv.created_at, datetime)
        assert conv.created_at.tzinfo == UTC

    def test_conversation_created_at_defaults_to_now(self) -> None:
        """Test created_at defaults to current time."""
        before = datetime.now(UTC)
        conv = Conversation(id=uuid4())
        after = datetime.now(UTC)

        assert before <= conv.created_at <= after

    def test_conversation_rejects_future_timestamp(self) -> None:
        """Test validation rejects created_at in the future."""
        future = datetime.now(UTC) + timedelta(hours=1)
        with pytest.raises(ValidationError):
            Conversation(id=uuid4(), created_at=future)

    def test_conversation_accepts_past_timestamp(self) -> None:
        """Test validation accepts past timestamps."""
        past = datetime.now(UTC) - timedelta(days=1)
        conv = Conversation(id=uuid4(), created_at=past)
        assert conv.created_at == past


class TestConversationTurn:
    """Test suite for ConversationTurn entity."""

    def test_create_turn_without_id(self) -> None:
        """Test creating turn before persistence (id=None)."""
        conv_id = uuid4()
        turn = ConversationTurn(
            conversation_id=conv_id,
            role="user",
            content="What is photosynthesis?",
            token_count=5,
        )

        assert turn.id is None
        assert turn.conversation_id == conv_id
        assert turn.role == "user"
        assert turn.content == "What is photosynthesis?"
        assert turn.token_count == 5

    def test_create_turn_with_id_after_persistence(self) -> None:
        """Test creating turn with id (after database persistence)."""
        conv_id = uuid4()
        turn = ConversationTurn(
            id=42,
            conversation_id=conv_id,
            role="assistant",
            content="Photosynthesis is...",
            token_count=150,
        )

        assert turn.id == 42

    def test_turn_rejects_invalid_role(self) -> None:
        """Test validation rejects roles other than user/assistant."""
        conv_id = uuid4()
        with pytest.raises(ValidationError):
            ConversationTurn(
                conversation_id=conv_id,
                role="system",
                content="Invalid role",
                token_count=2,
            )

    def test_turn_rejects_empty_content(self) -> None:
        """Test validation rejects empty content."""
        conv_id = uuid4()
        with pytest.raises(ValidationError):
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content="",
                token_count=0,
            )

    def test_turn_rejects_whitespace_only_content(self) -> None:
        """Test validation rejects whitespace-only content."""
        conv_id = uuid4()
        with pytest.raises(ValidationError):
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content="   \n\t  ",
                token_count=0,
            )

    def test_turn_strips_content_whitespace(self) -> None:
        """Test validation strips leading/trailing whitespace from content."""
        conv_id = uuid4()
        turn = ConversationTurn(
            conversation_id=conv_id,
            role="user",
            content="  Hello world  ",
            token_count=2,
        )

        assert turn.content == "Hello world"

    def test_turn_rejects_negative_token_count(self) -> None:
        """Test validation rejects negative token count."""
        conv_id = uuid4()
        with pytest.raises(ValidationError):
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content="Question",
                token_count=-1,
            )

    def test_turn_accepts_zero_token_count(self) -> None:
        """Test validation accepts zero token count (edge case)."""
        conv_id = uuid4()
        turn = ConversationTurn(
            conversation_id=conv_id,
            role="user",
            content="Question",
            token_count=0,
        )

        assert turn.token_count == 0

    def test_turn_rejects_future_timestamp(self) -> None:
        """Test validation rejects created_at in the future."""
        future = datetime.now(UTC) + timedelta(hours=1)
        with pytest.raises(ValidationError):
            ConversationTurn(
                conversation_id=uuid4(),
                role="user",
                content="Question",
                token_count=5,
                created_at=future,
            )


class TestTurnHistory:
    """Test suite for TurnHistory value object and budget enforcement."""

    def test_empty_history(self) -> None:
        """Test creating history from empty turn list."""
        history = TurnHistory.from_turns([])

        assert len(history.turns) == 0
        assert history.total_tokens == 0
        assert not history.is_trimmed

    def test_single_turn_under_budget(self) -> None:
        """Test single turn that fits under budget."""
        conv_id = uuid4()
        turn = ConversationTurn(
            conversation_id=conv_id,
            role="user",
            content="Question",
            token_count=100,
        )

        history = TurnHistory.from_turns([turn])

        assert len(history.turns) == 1
        assert history.total_tokens == 100
        assert not history.is_trimmed

    def test_multiple_turns_under_budget_and_count(self) -> None:
        """Test multiple turns within budget and count limits."""
        conv_id = uuid4()
        turns = [
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content=f"Question {i}",
                token_count=100,
            )
            for i in range(3)
        ]

        history = TurnHistory.from_turns(turns, max_tokens=2000, max_count=5)

        assert len(history.turns) == 3
        assert history.total_tokens == 300
        assert not history.is_trimmed

    def test_history_exceeding_token_budget(self) -> None:
        """Test trimming when total tokens exceed budget."""
        conv_id = uuid4()
        turns = [
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content=f"Question {i}",
                token_count=600,
            )
            for i in range(4)  # 2400 tokens total, budget 2000
        ]

        history = TurnHistory.from_turns(turns, max_tokens=2000, max_count=10)

        # Should keep last 3 turns (1800 tokens)
        assert len(history.turns) == 3
        assert history.total_tokens == 1800
        assert history.is_trimmed

    def test_history_exceeding_max_count(self) -> None:
        """Test trimming when turn count exceeds max_count."""
        conv_id = uuid4()
        turns = [
            ConversationTurn(
                conversation_id=conv_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Turn {i}",
                token_count=100,
            )
            for i in range(10)  # 10 turns, but max_count=5
        ]

        history = TurnHistory.from_turns(turns, max_tokens=5000, max_count=5)

        # Should keep last 5 turns
        assert len(history.turns) == 5
        assert history.is_trimmed

    def test_history_immutability(self) -> None:
        """Test TurnHistory is frozen (immutable)."""
        history = TurnHistory()

        with pytest.raises(ValidationError):
            history.turns = ()  # type: ignore

    def test_turn_history_to_llm_context_empty(self) -> None:
        """Test LLM context formatting for empty history."""
        history = TurnHistory()

        context = history.to_llm_context()
        assert context == ""

    def test_turn_history_to_llm_context_single_user_turn(self) -> None:
        """Test LLM context formatting with single user turn."""
        conv_id = uuid4()
        turn = ConversationTurn(
            conversation_id=conv_id,
            role="user",
            content="What is async/await?",
            token_count=4,
        )
        history = TurnHistory(turns=(turn,), total_tokens=4)

        context = history.to_llm_context()
        assert "User: What is async/await?" in context

    def test_turn_history_to_llm_context_multiple_turns(self) -> None:
        """Test LLM context formatting with multiple turns."""
        conv_id = uuid4()
        turns = (
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content="What is async/await?",
                token_count=4,
            ),
            ConversationTurn(
                conversation_id=conv_id,
                role="assistant",
                content="Async/await is a Python feature...",
                token_count=50,
            ),
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content="What about error handling?",
                token_count=4,
            ),
        )
        history = TurnHistory(turns=turns, total_tokens=58)

        context = history.to_llm_context()

        # Check all turns are in context
        assert "User: What is async/await?" in context
        assert "Assistant: Async/await is a Python feature..." in context
        assert "User: What about error handling?" in context

        # Check they're separated by double newlines
        assert "\n\n" in context

    def test_turn_history_preserves_turn_order(self) -> None:
        """Test that turns are formatted in order."""
        conv_id = uuid4()
        turns = (
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content="First",
                token_count=1,
            ),
            ConversationTurn(
                conversation_id=conv_id,
                role="assistant",
                content="Second",
                token_count=1,
            ),
            ConversationTurn(
                conversation_id=conv_id,
                role="user",
                content="Third",
                token_count=1,
            ),
        )
        history = TurnHistory(turns=turns, total_tokens=3)

        context = history.to_llm_context()
        first_pos = context.find("User: First")
        second_pos = context.find("Assistant: Second")
        third_pos = context.find("User: Third")

        assert first_pos < second_pos < third_pos
