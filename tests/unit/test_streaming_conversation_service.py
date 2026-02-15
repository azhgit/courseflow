"""Unit tests for StreamingConversationService (T030).

Tests conversation turn saving for streaming responses.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from courseflow.application.streaming_conversation_service import (
    StreamingConversationService,
)
from courseflow.domain.models import Conversation


@pytest.fixture
def mock_conversation_repo():
    """Create mocked conversation repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(mock_conversation_repo):
    """Create service with mocked repo."""
    return StreamingConversationService(mock_conversation_repo)


class TestStreamingConversationService:
    """Unit tests for StreamingConversationService (T030)."""

    @pytest.mark.asyncio
    async def test_save_streaming_turn_creates_new_conversation(
        self, service, mock_conversation_repo
    ) -> None:
        """T030: Saving turn creates new conversation when conversation_id is None."""
        # Arrange
        mock_conversation = MagicMock(spec=Conversation)
        mock_conversation.id = str(uuid4())
        mock_conversation_repo.create_conversation.return_value = mock_conversation
        mock_conversation_repo.add_turn.return_value = None

        query = "What is photosynthesis?"
        chunks = ["Photosynthesis", " is ", "the process"]

        # Act
        result_conv_id = await service.save_streaming_turn(
            query=query,
            chunks=chunks,
            conversation_id=None,
        )

        # Assert
        assert result_conv_id == str(mock_conversation.id)
        mock_conversation_repo.create_conversation.assert_called_once()
        # Should save user turn and assistant turn
        assert mock_conversation_repo.add_turn.call_count == 2

    @pytest.mark.asyncio
    async def test_save_streaming_turn_appends_to_existing_conversation(
        self, service, mock_conversation_repo
    ) -> None:
        """T030: Saving turn appends to existing conversation."""
        # Arrange
        existing_conv_id = str(uuid4())
        mock_conversation_repo.conversation_exists.return_value = True
        mock_conversation_repo.add_turn.return_value = None

        query = "What is AI?"
        chunks = ["AI", " stands for ", "Artificial Intelligence"]

        # Act
        result_conv_id = await service.save_streaming_turn(
            query=query,
            chunks=chunks,
            conversation_id=existing_conv_id,
        )

        # Assert
        assert result_conv_id == existing_conv_id
        from uuid import UUID

        mock_conversation_repo.conversation_exists.assert_called_once_with(UUID(existing_conv_id))
        assert mock_conversation_repo.add_turn.call_count == 2

    @pytest.mark.asyncio
    async def test_save_streaming_turn_reconstructs_answer(
        self, service, mock_conversation_repo
    ) -> None:
        """T030: Turn reconstruction joins chunks correctly."""
        # Arrange
        conv_id = str(uuid4())
        mock_conversation_repo.conversation_exists.return_value = True
        mock_conversation_repo.add_turn.return_value = None

        query = "Question?"
        chunks = ["Answer", " with", " multiple", " chunks"]

        # Act
        await service.save_streaming_turn(
            query=query,
            chunks=chunks,
            conversation_id=conv_id,
        )

        # Assert: Check that assistant turn was created with joined chunks
        calls = mock_conversation_repo.add_turn.call_args_list
        # First call is user turn, second is assistant turn
        assistant_turn = calls[1][0][0]
        assert assistant_turn.role == "assistant"
        assert assistant_turn.content == "Answer with multiple chunks"

    @pytest.mark.asyncio
    async def test_save_streaming_turn_tracks_token_count(
        self, service, mock_conversation_repo
    ) -> None:
        """T030: Token count is tracked correctly."""
        # Arrange
        conv_id = str(uuid4())
        mock_conversation_repo.conversation_exists.return_value = True
        mock_conversation_repo.add_turn.return_value = None

        query = "What?"
        chunks = ["Word1", " ", "word2", " ", "word3"]
        token_count = 3

        # Act
        await service.save_streaming_turn(
            query=query,
            chunks=chunks,
            conversation_id=conv_id,
            token_count=token_count,
        )

        # Assert
        calls = mock_conversation_repo.add_turn.call_args_list
        assistant_turn = calls[1][0][0]
        assert assistant_turn.token_count == token_count

    @pytest.mark.asyncio
    async def test_save_streaming_turn_empty_chunks_returns_conversation_id(
        self, service, mock_conversation_repo
    ) -> None:
        """T030: Empty chunks are handled gracefully (no persistence)."""
        # Arrange
        conv_id = str(uuid4())
        mock_conversation_repo.conversation_exists.return_value = True
        mock_conversation_repo.add_turn.return_value = None

        query = "What?"
        chunks: list[str] = []

        # Act
        result_conv_id = await service.save_streaming_turn(
            query=query,
            chunks=chunks,
            conversation_id=conv_id,
        )

        # Assert
        assert result_conv_id == conv_id
        # Should not attempt to save turns
        mock_conversation_repo.add_turn.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_streaming_turn_handles_persistence_errors(
        self, service, mock_conversation_repo
    ) -> None:
        """T030: Persistence errors are logged but don't crash stream."""
        # Arrange
        conv_id = str(uuid4())
        mock_conversation_repo.conversation_exists.return_value = True
        mock_conversation_repo.add_turn.side_effect = Exception("DB error")

        query = "What?"
        chunks = ["Answer"]

        # Act - should not raise
        result_conv_id = await service.save_streaming_turn(
            query=query,
            chunks=chunks,
            conversation_id=conv_id,
        )

        # Assert
        assert result_conv_id == conv_id

    @pytest.mark.asyncio
    async def test_save_streaming_turn_saves_both_user_and_assistant_turns(
        self, service, mock_conversation_repo
    ) -> None:
        """T030: Both user query and assistant response are saved."""
        # Arrange
        conv_id = str(uuid4())
        mock_conversation_repo.conversation_exists.return_value = True
        mock_conversation_repo.add_turn.return_value = None

        query = "User question"
        chunks = ["AI", " response"]

        # Act
        await service.save_streaming_turn(
            query=query,
            chunks=chunks,
            conversation_id=conv_id,
        )

        # Assert
        calls = mock_conversation_repo.add_turn.call_args_list
        assert len(calls) == 2

        user_turn = calls[0][0][0]
        assert user_turn.role == "user"
        assert user_turn.content == query

        assistant_turn = calls[1][0][0]
        assert assistant_turn.role == "assistant"
        assert assistant_turn.content == "AI response"
