import type { ChatMessage } from "../../types/chat";
import { SourcesList } from "./SourcesList";
import { PageReviewCard } from "./PageReviewCard";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-in-up">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-brand-gradient px-4 py-2.5 text-sm text-white shadow-soft sm:max-w-[75%]">
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start animate-fade-in-up">
      <div
        className={`max-w-[90%] rounded-2xl rounded-tl-sm border px-4 py-3 shadow-card sm:max-w-[80%] ${
          message.isError
            ? "border-rose-200 bg-rose-50"
            : "border-white bg-white"
        }`}
      >
        <p
          className={`text-sm leading-relaxed ${
            message.isError ? "text-rose-700" : "text-slate-700"
          }`}
        >
          {message.text}
        </p>

        {message.status === "needs_page_review" &&
          message.pageReferences &&
          message.pageReferences.length > 0 && (
            <PageReviewCard references={message.pageReferences} />
          )}

        {message.sources && message.sources.length > 0 && (
          <SourcesList sources={message.sources} />
        )}
      </div>
    </div>
  );
}
