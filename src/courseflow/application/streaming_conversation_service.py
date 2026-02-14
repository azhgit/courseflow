"""Conversation persistence service for streaming responses (T030-T031).

Handles saving streaming conversation turns to database:
- Reconstructs answer from streaming chunks
- Creates or appends to existing conversation
- Non-blocking (async) persistence
"""

import logging
from typing import Any
from uuid import UUID, uuid4

from courseflow.domain.models import ConversationTurn

logger = logging.getLogger(__name__)


class StreamingConversationService:
    """Service for persisting streaming conversations (T030)."""

    def __init__(self, conversation_repo: Any) -> None:
        """Initialize with conversation repository.

        Args:
            conversation_repo: Repository for conversation persistence
        """
        self.conversation_repo = conversation_repo

    async def save_streaming_turn(
        self,
        query: str,
        chunks: list[str],
        conversation_id: str | None = None,
        token_count: int = 0,
    ) -> str:
        """Save streaming turn to conversation history (T030-T031).

        Reconstructs answer from chunks and saves both user query and assistant response
        as separate turns in the conversation.

        Args:
            query: User's question
            chunks: List of text chunks streamed from LLM
            conversation_id: Optional UUID of existing conversation (creates new if None)
            token_count: Total tokens in response

        Returns:
            Conversation ID (created or existing)

        Raises:
            Exception: If persistence fails (logged but not re-raised)
        """
        try:
            # Reconstruct answer from chunks
            answer = "".join(chunks)

            if not answer:
                logger.warning("Streaming produced empty answer, not persisting")
                return conversation_id or str(uuid4())

            # Create or use existing conversation
            if conversation_id is None:
                # Create new conversation
                conversation = await self.conversation_repo.create_conversation()
                conv_id = str(conversation.id)
                logger.debug(f"Created new conversation for streaming: {conv_id}")
            else:
                # Validate existing conversation
                conv_id = conversation_id
                exists = await self.conversation_repo.conversation_exists(UUID(conv_id))
                if not exists:
                    logger.error(f"Conversation not found: {conv_id}")
                    raise ValueError(f"Conversation {conv_id} not found")
                logger.debug(f"Using existing conversation: {conv_id}")

            # Save user query turn
            user_turn = ConversationTurn(
                conversation_id=UUID(conv_id),
                role="user",
                content=query,
                token_count=len(query.split()),
            )
            await self.conversation_repo.add_turn(user_turn)
            logger.debug(f"Saved user turn to conversation: {conv_id}")

            # Save assistant response turn
            assistant_turn = ConversationTurn(
                conversation_id=UUID(conv_id),
                role="assistant",
                content=answer,
                token_count=token_count,
            )
            await self.conversation_repo.add_turn(assistant_turn)
            logger.debug(f"Saved assistant turn to conversation: {conv_id}")

            return conv_id

        except Exception as e:
            logger.error(f"Failed to save streaming turn: {e}")
            # Don't re-raise - streaming should complete even if persistence fails
            return conversation_id or str(uuid4())
