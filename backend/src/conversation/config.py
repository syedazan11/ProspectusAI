"""
config.py

Configuration for the ProspectusAI conversation layer.

Purpose
-------
`ConversationConfig` centralizes the tunable numeric/threshold values
that conversation-layer behavior will depend on, so that future
components (analyzer, history manager, memory manager -- none of which
are designed in this task) read from one injected object instead of
hardcoding constants throughout the codebase.

This file defines values only. It does not decide when a summary gets
triggered, when a topic goes stale, or when a message crosses the
follow-up threshold -- that decision logic belongs to the components
that consume this config, not to the config itself.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationConfig:
    """
    Tunable thresholds and capacities for one conversation layer
    deployment.

    Frozen because configuration is meant to be loaded once and shared
    (safely, without accidental mutation) across every session and
    component that depends on it.

    Fields
    ------
    max_history_messages:
        Maximum number of `ConversationMessage` instances kept in
        `ConversationState.recent_messages` before older ones are folded
        into a `ConversationSummary` and evicted. Bounds memory/token
        usage for anything that later serializes recent history.
    summary_interval_turns:
        How many turns should pass between re-generating
        `ConversationState.summary`. Decouples "how often we compress"
        from "how much raw history we keep" (`max_history_messages`),
        since a service may want to summarize more or less frequently
        than the raw window fills up.
    memory_capacity:
        Maximum number of entries allowed in `SessionMemory.entries` for
        a single session. Prevents unbounded growth of session memory
        over a very long-lived conversation.
    follow_up_confidence_threshold:
        Minimum confidence required for a turn to be treated as
        `ConversationIntent.FOLLOW_UP_QUERY` of the active topic rather
        than a new, independent query. Below this threshold, a future
        analyzer would prefer `TopicAction.START_TOPIC` /
        `TopicAction.SWITCH_TOPIC` over `TopicAction.CONTINUE_TOPIC`.
    clarification_confidence_threshold:
        Minimum confidence required for *any* intent to be accepted at
        face value. Below this threshold, a future analyzer would prefer
        `ConversationIntent.AMBIGUOUS` /
        `ResponseAction.ASK_CLARIFICATION` over acting on the raw
        classification. Deliberately a separate value from
        `follow_up_confidence_threshold`: the two thresholds gate
        different decisions (whether to trust the intent at all, versus
        whether to treat it as a continuation) and production tuning
        will often need to move them independently.
    topic_idle_timeout_seconds:
        How long (in seconds) a topic may go untouched
        (`TopicContext.last_active_at`) before it is considered stale and
        eligible for `TopicAction.CLEAR_TOPIC`. `None` disables idle-based
        clearing entirely, leaving topic lifetime governed only by
        explicit switches.
    memory_entry_default_ttl_seconds:
        Default time-to-live applied to a new `MemoryEntry.expires_at`
        when a component doesn't specify one explicitly. `None` means
        entries have no expiry by default and persist for the life of
        the session (subject to `memory_capacity`).
    """

    max_history_messages: int = 20
    summary_interval_turns: int = 10
    memory_capacity: int = 50
    follow_up_confidence_threshold: float = 0.6
    clarification_confidence_threshold: float = 0.4
    topic_idle_timeout_seconds: int | None = 600
    memory_entry_default_ttl_seconds: int | None = None