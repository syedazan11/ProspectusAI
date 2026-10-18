from .models import ConversationTopic
from .state import ConversationState


class ContextResolver:

    def resolve(
        self,
        topic: ConversationTopic,
        state: ConversationState,
    ) -> ConversationTopic:

        if state.topic is None:
            return topic

        return self._merge(
            topic,
            state.topic,
        )

    def _merge(
        self,
        current: ConversationTopic,
        previous: ConversationTopic,
    ) -> ConversationTopic:

        entities = current.entities

        if (
            not entities
            and current.subject is not None
            and previous.entities
        ):
            entities = previous.entities

        subject = current.subject

        if (
            subject is None
            and previous.subject
        ):
            subject = previous.subject

        codes = current.codes

        if (
            not codes
            and previous.codes
        ):
            codes = previous.codes

        return ConversationTopic(
            entities=entities,
            subject=subject,
            codes=codes,
            confidence=max(
                current.confidence,
                previous.confidence,
            ),
            is_follow_up=(
                not current.entities
                and previous.entities
            ),
        )
    