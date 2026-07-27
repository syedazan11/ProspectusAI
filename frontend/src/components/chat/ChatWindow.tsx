import { useEffect, useRef, useState } from "react";
import type {
  ChatMessage,
  ChatSummary,
  StoredMessage,
} from "../../types/chat";
import {
  createChat,
  getChatMessages,
  listChats,
  streamChatMessage,
} from "../../services/chatService";
import { ApiError } from "../../services/api";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ExampleChips } from "./ExampleChips";

interface ChatWindowProps {
  activeChatId: string | null;
  onActiveChatChange: (chatId: string) => void;
  onChatsChange: (chats: ChatSummary[]) => void;
}

function toChatMessage(
  message: StoredMessage,
): ChatMessage {
  return {
    id: message.id,
    role: message.role,
    text: message.content,
    sources: message.sources,
    pageReferences: message.page_references,
    createdAt: new Date(
      message.created_at,
    ).getTime(),
  };
}

export function ChatWindow({
  activeChatId,
  onActiveChatChange,
  onChatsChange,
}: ChatWindowProps) {
  const [messages, setMessages] = useState<
    ChatMessage[]
  >([]);
  const [isLoading, setIsLoading] =
    useState(false);
  const [isLoadingHistory, setIsLoadingHistory] =
    useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const skipNextHistoryLoad = useRef(false);

  useEffect(() => {
    if (!activeChatId) {
      setMessages([]);
      return;
    }

    if (skipNextHistoryLoad.current) {
      skipNextHistoryLoad.current = false;
      return;
    }

    let cancelled = false;

    async function loadHistory() {
      setIsLoadingHistory(true);

      try {
        const response =
          await getChatMessages(activeChatId!);

        if (!cancelled) {
          setMessages(
            response.messages.map(toChatMessage),
          );
        }
      } catch {
        if (!cancelled) {
          setMessages([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false);
        }
      }
    }

    void loadHistory();

    return () => {
      cancelled = true;
    };
  }, [activeChatId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  async function ensureChat(): Promise<string> {
    if (activeChatId) {
      return activeChatId;
    }

    const chat = await createChat();

    skipNextHistoryLoad.current = true;
    onActiveChatChange(chat.id);

    const chats = await listChats();
    onChatsChange(chats);

    return chat.id;
  }

  async function handleSend(question: string) {
    if (isLoading) {
      return;
    }

    const optimisticUserMessage: ChatMessage = {
      id: `pending-${Date.now()}`,
      role: "user",
      text: question,
      createdAt: Date.now(),
    };

    setMessages((previous) => [
      ...previous,
      optimisticUserMessage,
    ]);
    setIsLoading(true);

    try {
      const chatId = await ensureChat();

      const streamingMessageId =
        `streaming-${Date.now()}`;

      setMessages((previous) => [
        ...previous,
        {
          id: streamingMessageId,
          role: "assistant",
          text: "",
          createdAt: Date.now(),
        },
      ]);

      await streamChatMessage(
        chatId,
        question,
        {
          onToken(token) {
            setMessages((previous) =>
              previous.map((message) =>
                message.id === streamingMessageId
                  ? {
                      ...message,
                      text: message.text + token,
                    }
                  : message,
              ),
            );
          },

          onDone(response) {
            setMessages((previous) =>
              previous.map((message) =>
                message.id === streamingMessageId
                  ? {
                      id: response.message.id,
                      role: "assistant",
                      text: response.answer,
                      status: response.status,
                      sources: response.sources,
                      pageReferences:
                        response.page_references,
                      createdAt: new Date(
                        response.message.created_at,
                      ).getTime(),
                    }
                  : message,
              ),
            );
          },
        },
      );

      const chats = await listChats();
      onChatsChange(chats);
    } catch (error) {
      const text =
        error instanceof ApiError
          ? error.message
          : "Something went wrong while getting an answer. Please try again.";

      setMessages((previous) => [
        ...previous,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          text,
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
      className="chat-scroll flex-1 space-y-6 overflow-y-auto px-6 py-6"
    >
      {isLoadingHistory && (
        <div className="flex h-full items-center justify-center text-sm text-slate-400">
          Loading conversation...
        </div>
      )}

      {!isLoadingHistory && !hasMessages && (
        <div className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center">
          <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[#163A6B] shadow-xl">
            <span className="text-4xl">🎓</span>
          </div>

          <div>
            <h2 className="text-4xl font-bold text-[#163A6B]">
              Ask me anything about the NED Prospectus
            </h2>

            <p className="mt-3 max-w-xl text-lg leading-8 text-slate-500">
              Ask about admissions, eligibility, fees,
              programmes, deadlines and official
              prospectus information.
            </p>
          </div>

          <ExampleChips
            onSelect={handleSend}
            disabled={isLoading}
          />
        </div>
      )}

      {!isLoadingHistory &&
        messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
          />
        ))}

      {isLoading && (
        <div className="flex items-start gap-3 animate-fade-in-up">
          {/* AI Avatar */}
          <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-full bg-[#163A6B] text-white font-bold shadow-md">
            AI
          </div>

          {/* Typing Bubble */}
          <div className="flex items-center gap-2 rounded-3xl rounded-tl-md border border-slate-200 bg-white px-5 py-4 shadow-md">
            <span
              className="typing-dot h-2 w-2 rounded-full bg-[#163A6B]"
              style={{ animationDelay: "0ms" }}
            />
            <span
              className="typing-dot h-2 w-2 rounded-full bg-[#163A6B]"
              style={{ animationDelay: "150ms" }}
            />
            <span
              className="typing-dot h-2 w-2 rounded-full bg-[#163A6B]"
              style={{ animationDelay: "300ms" }}
            />
          </div>
        </div>
      )}
    </div>

    <div className="mt-4 shrink-0 border-t border-slate-200 bg-white pt-4">
      <ChatInput
        onSend={handleSend}
        isLoading={isLoading || isLoadingHistory}
      />
    </div>
  </div>
); }