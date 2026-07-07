import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../../types/chat";
import { sendChatMessage } from "../../services/chatService";
import { ApiError } from "../../services/api";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ExampleChips } from "./ExampleChips";

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  async function handleSend(question: string) {
    if (isLoading) return; // guard against duplicate sends

    const userMessage: ChatMessage = {
      id: makeId(),
      role: "user",
      text: question,
      createdAt: Date.now(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(question);
      const assistantMessage: ChatMessage = {
        id: makeId(),
        role: "assistant",
        text: response.answer,
        status: response.status,
        sources: response.sources,
        pageReferences: response.page_references,
        createdAt: Date.now(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Something went wrong while getting an answer. Please try again.";
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          text: message,
          isError: true,
          createdAt: Date.now(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-full flex-col">
      <div
        ref={scrollRef}
        className="chat-scroll flex-1 space-y-4 overflow-y-auto px-1 py-4"
      >
        {!hasMessages && (
          <div className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center">
            <div className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-gradient text-2xl shadow-soft">
              🎓
            </div>
            <div>
              <h2 className="font-display text-xl font-semibold text-slate-800">
                Ask me anything about the prospectus
              </h2>
              <p className="mt-1 max-w-sm text-sm text-slate-500">
                Seats, fees, eligibility, deadlines — I'll answer from the
                official university prospectus.
              </p>
            </div>
            <ExampleChips onSelect={handleSend} disabled={isLoading} />
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-white bg-white px-4 py-3 shadow-card">
              <span className="typing-dot h-1.5 w-1.5 rounded-full bg-brand-purple" />
              <span
                className="typing-dot h-1.5 w-1.5 rounded-full bg-brand-purple"
                style={{ animationDelay: "150ms" }}
              />
              <span
                className="typing-dot h-1.5 w-1.5 rounded-full bg-brand-purple"
                style={{ animationDelay: "300ms" }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="mt-2 shrink-0 space-y-2">
        {hasMessages && (
          <div className="chat-scroll -mx-1 overflow-x-auto px-1 pb-1">
            <ExampleChips onSelect={handleSend} disabled={isLoading} />
          </div>
        )}
        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </div>
    </div>
  );
}
