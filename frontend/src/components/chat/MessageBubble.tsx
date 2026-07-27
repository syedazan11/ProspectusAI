import type { ChatMessage } from "../../types/chat";
import { SourcesList } from "./SourcesList";
import { PageReviewCard } from "./PageReviewCard";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end animate-fade-in-up">
        <div
          className="
            max-w-[85%]
            rounded-3xl
            rounded-br-md
            bg-[#163A6B]
            px-5
            py-3
            text-[15px]
            leading-7
            text-white
            shadow-lg
            sm:max-w-[70%]
            break-words
          "
        >
          {message.text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 animate-fade-in-up">
      {/* AI Avatar */}
      <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#163A6B] text-white font-bold shadow-md">
        AI
      </div>

      <div
        className={`
          max-w-[90%]
          rounded-3xl
          rounded-tl-md
          border
          px-5
          py-4
          shadow-md
          sm:max-w-[80%]
          transition-all
          ${
            message.isError
              ? "border-red-200 bg-red-50"
              : "border-slate-200 bg-white"
          }
        `}
      >
        <div
          className={`whitespace-pre-wrap text-[15px] leading-7 ${
            message.isError
              ? "text-red-700"
              : "text-slate-700"
          }`}
        >
          {message.text}
        </div>

        {message.pageReferences &&
          message.pageReferences.length > 0 && (
            <div className="mt-5">
              <PageReviewCard references={message.pageReferences} />
            </div>
          )}

        {message.sources &&
          message.sources.length > 0 && (
            <div className="mt-5 border-t border-slate-100 pt-4">
              <SourcesList sources={message.sources} />
            </div>
          )}
      </div>
    </div>
  );
}