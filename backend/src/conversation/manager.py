from .analyzer import ConversationAnalyzer
from .query_rewriter import QueryRewriter
from .state import ConversationState
from .models import ConversationResult


class ConversationManager:

    def __init__(
        self,
    ):

        self._analyzer = ConversationAnalyzer()

        self._rewriter = QueryRewriter()

    def process(
        self,
        *,
        message: str,
        state: ConversationState,
    ):

        decision = self._analyze(
            message,
            state,
        )
        rewritten_query = self._rewrite(
            message,
            state,
        )

        return ConversationResult(
            decision=decision,
            rewritten_query=rewritten_query,
            state=state,
        )

    def _analyze(
        self,
        message: str,
        state: ConversationState,
    ):

        return self._analyzer.analyze(
            message=message,
            state=state,
        )

    def _rewrite(
        self,
        message: str,
        state: ConversationState,
    ) -> str:

        return self._rewriter.rewrite(
            original=message,
            topic=state.topic,
        )