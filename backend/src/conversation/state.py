"""
state.py

Session-scoped conversation state for ProspectusAI.

Purpose
-------
`ConversationState` is the single object that represents everything the
conversation layer knows about one active chat session, at rest. It is
the thing a session store would persist/load and the thing every future
component (analyzer, router, handlers) would read from and write back to
-- none of which are designed in this task.

This module holds no logic at all: no methods, no derived properties, no
mutation helpers. Appending messages, rotating summaries, evicting
history, and bumping the turn counter are all policy decisions
(governed by `ConversationConfig`) that belong to a future service, not
to the state object itself. `ConversationState` never references
retrieval, vector search, database clients, or LLM clients either: those
are collaborators of components built *on top of* this state, not part
of the state itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .models import (
    ConversationDecision,
    ConversationMessage,
    ConversationSummary,
    ConversationTopic,
    SessionMemory,
    TopicContext,
)


@dataclass(slots=True)
class ConversationState:
    """
    Everything required to represent one active chat session.

    Not frozen: unlike the individual records it holds (messages,
    decisions, summaries, topics -- all immutable snapshots), the state
    object itself is the mutable "current position" of a session, and is
    expected to be updated in place by whatever service owns the
    conversation turn loop (out of scope here).

    Fields
    ------
    session_id:
        Stable unique identifier for the session. The natural key for
        loading/saving this object; persistence itself is out of scope.
    created_at:
        When the session was first created.
    updated_at:
        When the session was last modified in any way. Kept separate
        from individual message timestamps so the *session's* freshness
        can be checked in O(1) without inspecting history.
    turn_counter:
        Monotonically increasing count of turns processed in this
        session. Distinct from `len(recent_messages)`, which shrinks as
        older messages are summarized/evicted -- `turn_counter` is the
        durable, ever-increasing figure that `ConversationMessage.turn_number`
        and `ConversationSummary.covers_up_to_turn` are anchored to.
    current_topic:
        The active `TopicContext`, or `None` if no topic is currently
        open. Replaced wholesale (not mutated) whenever a `TopicAction`
        other than `CONTINUE_TOPIC`/`NONE` is applied, consistent with
        `TopicContext` being immutable.
    recent_messages:
        A bounded window of the most recent `ConversationMessage`
        instances, newest last. "Bounded" is a policy
        (`ConversationConfig.max_history_messages`) enforced by whatever
        service manages the session, not by this class.
    summary:
        The current compressed representation of history older than
        `recent_messages`, or `None` if no summarization has happened
        yet. A single field, not a list: summaries are expected to be
        periodically re-produced (per
        `ConversationConfig.summary_interval_turns`) and replace the
        previous one, not accumulate.
    memory:
        The session's `SessionMemory` container. Always present (never
        `None`) so consumers don't need a null check to read/write
        memory; an empty session starts with an empty `SessionMemory`.
    last_decision:
        The most recent `ConversationDecision` produced for this
        session, or `None` before the first turn. Useful for anything
        that needs "what did we just decide" without re-deriving it
        (e.g. follow-up detection comparing the new turn to the last
        decision's domain/topic).
    """

    # session_id: str
    # created_at: datetime
    # updated_at: datetime
    # turn_counter: int = 0
    # current_topic: TopicContext | None = None
    # recent_messages: list[ConversationMessage] = field(default_factory=list)
    # summary: ConversationSummary | None = None
    # memory: SessionMemory = field(default_factory=SessionMemory)
    # last_decision: ConversationDecision | None = None

    topic: ConversationTopic | None = None

    last_action: str | None = None

    turns: list[str] = field(
        default_factory=list,
    )

    user_name: str | None = None


def update(
        self,
        *,
        message: str,
        action: str,
        topic: ConversationTopic | None,
    ) -> None:

        self.last_action = action

        self.turns.append(message)

        if len(self.turns) > 20:
            self.turns.pop(0)

        if topic is not None:
            self.topic = topic

