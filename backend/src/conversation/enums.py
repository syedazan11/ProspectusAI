"""
enums.py

Enumerations used across the ProspectusAI conversation layer.

Purpose
-------
These enums remove magic strings from every conversation-level decision.
They describe *what kind of thing* is happening in a turn (who is
speaking, what the user wants, which subject-matter bucket applies, how
the active topic should change, and how the system should respond) --
never *how* to fulfill it. There is no business logic, prompt text, or
routing behavior here: only closed, named vocabularies that the rest of
the system (analyzer, router, handlers -- none of which are designed in
this task) can depend on without importing string literals.

All members are domain-independent, with one deliberate, explicitly
justified exception documented on ConversationDomain.PROSPECTUS.

Design notes
------------
- Every enum subclasses `str, Enum`. This keeps members safely comparable
  (`intent == ConversationIntent.GREETING`) while also being trivially
  JSON- and log-serializable (`json.dumps(intent)` just works, and log
  lines print the value rather than a Python repr).
- New members can be appended to any enum without breaking existing code
  that pattern-matches on the members already present (additive, not
  breaking, extensibility).
"""

from enum import Enum


class MessageRole(str, Enum):
    """
    Who authored a given ConversationMessage.

    Not requested explicitly by name, but required by ConversationMessage
    in models.py -- message authorship is a closed set and belongs here
    rather than as a free-text field.
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationIntent(str, Enum):
    """
    Fine-grained classification of a single user turn.

    This is the most granular vocabulary in the conversation layer. It
    spans social moves (GREETING, GOODBYE, THANKS), meta moves
    (INTRODUCTION, CAPABILITY), domain moves (DOMAIN_QUERY,
    FOLLOW_UP_QUERY), memory moves (STORE_MEMORY, RECALL_MEMORY), and
    failure/edge moves (OUT_OF_DOMAIN, UNINTELLIGIBLE, AMBIGUOUS,
    UNKNOWN).

    Renamed from the prompt's suggestions, with rationale:
      - PROSPECTUS_QUERY -> DOMAIN_QUERY
        The intent vocabulary itself must stay domain-independent so it
        is reusable for any assistant built on this same foundation.
        "Which domain the query belongs to" is answered by
        ConversationDomain, not by the intent name.
      - FOLLOW_UP -> FOLLOW_UP_QUERY
        Makes the pairing with DOMAIN_QUERY explicit: this is a follow-up
        *to* a domain query, not a generic conversational follow-up.
      - CLARIFICATION -> AMBIGUOUS
        CLARIFICATION described two different things in the prompt's
        examples: the *state* of the user's message (too vague to
        classify) and the *action* of asking the user to clarify. Only
        the first is an intent -- what the assistant should do about it
        is a ResponseAction (see ResponseAction.ASK_CLARIFICATION).
      - GIBBERISH -> UNINTELLIGIBLE
        Same meaning, production-appropriate wording.
      - Added UNKNOWN as an explicit fallback for "classifier produced no
        confident intent", distinct from AMBIGUOUS ("classifier saw a
        real but underspecified request") and distinct from
        UNINTELLIGIBLE ("input was not coherent text at all").
    """

    GREETING = "greeting"
    GOODBYE = "goodbye"
    THANKS = "thanks"
    INTRODUCTION = "introduction"
    CAPABILITY = "capability"
    DOMAIN_QUERY = "domain_query"
    FOLLOW_UP_QUERY = "follow_up_query"
    STORE_MEMORY = "store_memory"
    RECALL_MEMORY = "recall_memory"
    OUT_OF_DOMAIN = "out_of_domain"
    UNINTELLIGIBLE = "unintelligible"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class ConversationDomain(str, Enum):
    """
    Coarse-grained subject-matter bucket for a turn.

    Broader and coarser than ConversationIntent: several intents map to
    the same domain (e.g. GREETING, GOODBYE, THANKS, CAPABILITY all live
    under CONVERSATION), while DOMAIN_QUERY / FOLLOW_UP_QUERY map to
    PROSPECTUS.

    PROSPECTUS is the one deliberately product-specific member in this
    entire file. It is kept as a plain enum value -- rather than
    generalized into something like PRIMARY_DOMAIN resolved elsewhere --
    because ProspectusAI's core subject matter is a fixed, product-level
    fact, and every other model in this layer (ConversationMessage,
    TopicContext, MemoryEntry, etc.) stays fully generic regardless of
    this one value existing. Renaming it would only move the coupling
    into a mapping table someone still has to define; it would not
    remove it.
    """

    CONVERSATION = "conversation"
    PROSPECTUS = "prospectus"
    OUT_OF_DOMAIN = "out_of_domain"
    UNKNOWN = "unknown"


class TopicAction(str, Enum):
    """
    The transition to apply to the active topic (TopicContext) as a
    result of processing a turn.

    Kept orthogonal to ConversationIntent on purpose: intent answers
    "what did the user want", topic action answers "what happens to the
    thread of conversation as a result". The same intent can map to
    different topic actions depending on context (e.g. a DOMAIN_QUERY can
    START_TOPIC if none is active, or SWITCH_TOPIC if one already is).
    """

    NONE = "none"
    START_TOPIC = "start_topic"
    CONTINUE_TOPIC = "continue_topic"
    SWITCH_TOPIC = "switch_topic"
    CLEAR_TOPIC = "clear_topic"


class ResponseAction(str, Enum):
    """
    The high-level instruction describing how a response should be
    produced, as decided by the (future) conversation analyzer.

    This is the only enum in the file that speaks about downstream
    behavior, and even then strictly at the level of "what category of
    action", never "how" -- no prompt names, no retriever parameters, no
    handler references. Mapping a ResponseAction to a concrete handler is
    routing logic, and routing logic is explicitly out of scope here.
    """

    DIRECT_RESPONSE = "direct_response"
    RETRIEVE = "retrieve"
    ASK_CLARIFICATION = "ask_clarification"
    REJECT = "reject"
    STORE_MEMORY = "store_memory"
    RECALL_MEMORY = "recall_memory"