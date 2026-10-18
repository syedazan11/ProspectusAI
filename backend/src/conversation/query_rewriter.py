from .models import ConversationTopic


class QueryRewriter:

    def rewrite(
        self,
        *,
        original: str,
        topic: ConversationTopic | None,
    ) -> str:

        if topic is None:
            return original

        if not self.should_rewrite(topic):
            return original

        return self._rewrite(
            original,
            topic,
        )

    def _rewrite(
        self,
        query: str,
        topic: ConversationTopic,
    ) -> str:

        rewritten = query.strip()

        prefix = []

        entity_text = " ".join(
            topic.entities
        ).strip()

        if (
            entity_text
            and entity_text.casefold()
            not in rewritten.casefold()
        ):
            prefix.append(entity_text)

        if (
            topic.subject
            and topic.subject.casefold()
            not in rewritten.casefold()
        ):
            prefix.append(topic.subject)

        if not prefix:
            return rewritten

        return (
            " ".join(prefix)
            + " "
            + rewritten
        ).strip()
    
    def should_rewrite(
        self,
        topic: ConversationTopic,
    ) -> bool:

        return (
            topic.is_follow_up
            or bool(topic.entities)
        )