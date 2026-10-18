import { useEffect, useRef, useState } from "react";
import type {
  ChatMessage,
  // ChatSummary,
  StoredMessage,
} from "../../types/chat";
import {
  // createChat,
  getChatMessages,
  // listChats,
  streamChatMessage,
} from "../../services/chatService";
import { ApiError } from "../../services/api";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { ExampleChips } from "./ExampleChips";

// interface ChatWindowProps {
//   activeChatId: string | null;
//   onActiveChatChange: (chatId: string) => void;
//   onChatsChange: (chats: ChatSummary[]) => void;
// }
interface ChatWindowProps {
  activeChatId: string | null;
  onActiveChatChange: (chatId: string) => void;
  onNewChat: () => void;
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
  onNewChat,
  // onChatsChange,
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
  const tokenQueueRef = useRef("");
  const tokenFlushTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!activeChatId) {
      console.log("[HISTORY] activeChatId is null -> clearing messages");
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

        console.log(
          "[HISTORY] received:",
          response.messages,
        );

        if (!cancelled) {
          setMessages(
            response.messages.map(toChatMessage),
          );
        }
      // } catch {
      //   if (!cancelled) {
      //     setMessages([]);
      //   }
      // } 
      } catch (error) {
        if (!cancelled) {
          setMessages([]);

          if (
            error instanceof ApiError &&
            error.status === 404
          ) {
            sessionStorage.removeItem(
              "prospectusai_active_chat_id",
            );
            onActiveChatChange("");
          }
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
      behavior: "auto",
    });
  }, [messages, isLoading]);

  useEffect(() => {
    return () => {
      if (tokenFlushTimerRef.current !== null) {
        window.clearTimeout(tokenFlushTimerRef.current);
      }
    };
  }, []);

  // async function ensureChat(): Promise<string> {
  //   if (activeChatId) {
  //     return activeChatId;
  //   }

  //   const chat = await createChat();

  //   skipNextHistoryLoad.current = true;
  //   onActiveChatChange(chat.id);

  //   void listChats()
  //     .then((chats) => {
  //       onChatsChange(chats);
  //     })
  //     .catch(() => {
  //       // Chat creation already succeeded.
  //       // A sidebar refresh failure should not block sending.
  //     });

  //   // const chats = await listChats();
  //   // onChatsChange(chats);

  //   return chat.id;
  // }

  async function ensureChat(): Promise<string> {
    if (activeChatId) {
      return activeChatId;
    }

    const chatId = crypto.randomUUID();

    sessionStorage.setItem(
      "prospectusai_active_chat_id",
      chatId,
    );

    skipNextHistoryLoad.current = true;
    onActiveChatChange(chatId);

    return chatId;
  }

  async function handleSend(question: string) {
    if (isLoading) {
      return;
    }

    const sendStart = performance.now();

    console.log(
      "[FRONTEND TIMING] handleSend START",
    );

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
      console.log(
        `[FRONTEND TIMING] before ensureChat: ${
          performance.now() - sendStart
        }ms`,
      );

      const chatId = await ensureChat();

      console.log(
        `[FRONTEND TIMING] after ensureChat: ${
          performance.now() - sendStart
        }ms`,
      );

      // const streamingMessageId =
      //   `streaming-${Date.now()}`;

      // setMessages((previous) => [
      //   ...previous,
      //   {
      //     id: streamingMessageId,
      //     role: "assistant",
      //     text: "",
      //     createdAt: Date.now(),
      //   },
      // ]);

      let firstTokenReceived = false;

      console.log(
        `[FRONTEND TIMING] BEFORE streamChatMessage: ${
          performance.now() - sendStart
        }ms`,
      );

      await streamChatMessage(
        chatId,
        question,
        {
            // onToken(token) {
            //     if (!firstTokenReceived) {
            //         firstTokenReceived = true;

            //         setIsLoading(false);

            //         console.log(
            //             `[FRONTEND TIMING] FIRST TOKEN: ${
            //                 performance.now() - sendStart
            //             }ms`,
            //         );

            //         setMessages((previous) => [
            //             ...previous,
            //             {
            //                 id: `streaming-${Date.now()}`,
            //                 role: "assistant",
            //                 text: token,
            //                 createdAt: Date.now(),
            //             },
            //         ]);

            //         return;
            //     }

            //     setMessages((previous) =>
            //         previous.map((message) =>
            //             message.role === "assistant" &&
            //             message.id.startsWith("streaming-")
            //                 ? {
            //                       ...message,
            //                       text: message.text + token,
            //                   }
            //                 : message,
            //         ),
            //     );
            // },
            onToken(token) {
                if (!firstTokenReceived) {
                    firstTokenReceived = true;

                    setIsLoading(false);

                    console.log(
                        `[FRONTEND TIMING] FIRST TOKEN: ${
                            performance.now() - sendStart
                        }ms`,
                    );

                    setMessages((previous) => [
                        ...previous,
                        {
                            id: `streaming-${Date.now()}`,
                            role: "assistant",
                            text: "",
                            createdAt: Date.now(),
                        },
                    ]);
                }

                tokenQueueRef.current += token;

                if (tokenFlushTimerRef.current !== null) {
                    return;
                }

                tokenFlushTimerRef.current = window.setTimeout(() => {
                    const queuedTokens = tokenQueueRef.current;

                    tokenQueueRef.current = "";
                    tokenFlushTimerRef.current = null;

                    if (!queuedTokens) {
                        return;
                    }

                    setMessages((previous) =>
                        previous.map((message) =>
                            message.role === "assistant" &&
                            message.id.startsWith("streaming-")
                                ? {
                                      ...message,
                                      text:
                                          message.text +
                                          queuedTokens,
                                  }
                                : message,
                        ),
                    );
                }, 25);
            },

            onReplace(content) {
                setMessages((previous) =>
                    previous.map((message) =>
                        message.id.startsWith("streaming-")
                            ? {
                                  ...message,
                                  text: content,
                              }
                            : message,
                    ),
                );
            },

            onDone(response) {
              console.log("[DONE RESPONSE]", response);
              console.log(
                    `[FRONTEND TIMING] DONE EVENT: ${
                        performance.now() - sendStart
                    }ms`,
                );

                setMessages((previous) => {
                    const hasStreamingMessage =
                        previous.some(
                            (message) =>
                                message.id.startsWith(
                                    "streaming-",
                                ),
                        );

                    if (!hasStreamingMessage) {
                        return [
                            ...previous,
                            {
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
                            },
                        ];
                    }

                    return previous.map(
                        (message) =>
                            message.id.startsWith(
                                "streaming-",
                            )
                                ? {
                                      id: response.message.id,
                                      role: "assistant",
                                      text: response.answer,
                                      status: response.status,
                                      sources:
                                          response.sources,
                                      pageReferences:
                                          response.page_references,
                                      createdAt:
                                          new Date(
                                              response.message.created_at,
                                          ).getTime(),
                                  }
                                : message,
                    );
                });
            },
        },
    );

    // void listChats()
    //     .then((chats) => {
    //         onChatsChange(chats);
    //     })
    //     .catch(() => {
    //         // Chat response is already complete.
    //         // A sidebar refresh failure should not affect the answer.
    //     });

      console.log(
        `[FRONTEND TIMING] streamChatMessage RETURNED: ${
          performance.now() - sendStart
        }ms`,
      );

      // console.log(
      //   `[FRONTEND TIMING] BEFORE final listChats: ${
      //     performance.now() - sendStart
      //   }ms`,
      // );

      // const chats = await listChats();
      // console.log(
      //   `[FRONTEND TIMING] AFTER final listChats: ${
      //     performance.now() - sendStart
      //   }ms`,
      // );
      // onChatsChange(chats);
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
      console.log(
        `[FRONTEND TIMING] handleSend END: ${
          performance.now() - sendStart
        }ms`,
      );
      setIsLoading(false);
    }
  }

  const hasMessages = messages.length > 0;


  return (
    <div className="flex h-full flex-col">
      {/* Chat messages */}
      <div
        ref={scrollRef}
        className="chat-scroll flex-1 overflow-y-auto px-4 py-6 sm:px-6"
      >
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-5">
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
      </div>

      {/* Input area */}
      <div className="shrink-0 bg-transparent px-4 pb-3 pt-2 sm:px-6">
        <div className="mx-auto w-full max-w-4xl">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onNewChat}
              disabled={isLoading}
              className="
                shrink-0
                rounded-xl
                border border-slate-300
                bg-white
                px-4 py-3
                text-sm
                font-medium
                text-slate-600
                shadow-sm
                transition
                hover:border-slate-400
                hover:bg-slate-50
                disabled:cursor-not-allowed
                disabled:opacity-50
              "
            >
              + New Chat
            </button>

            <div className="min-w-0 flex-1">
              <ChatInput
                onSend={handleSend}
                isLoading={isLoading || isLoadingHistory}
              />
            </div>
          </div>

          <p className="mt-2 text-center text-[11px] text-slate-400">
            ProspectusAI may make mistakes. Please verify important information
            with the official NED prospectus.
          </p>
        </div>
      </div>
    </div>
  );
}

//   return (
//   <div className="flex h-full flex-col">
//     <div
//       ref={scrollRef}
//       className="chat-scroll flex-1 space-y-6 overflow-y-auto px-6 py-6"
//     >
//       {isLoadingHistory && (
//         <div className="flex h-full items-center justify-center text-sm text-slate-400">
//           Loading conversation...
//         </div>
//       )}

//       {!isLoadingHistory && !hasMessages && (
//         <div className="flex h-full flex-col items-center justify-center gap-4 px-4 text-center">
//           <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[#163A6B] shadow-xl">
//             <span className="text-4xl">🎓</span>
//           </div>

//           <div>
//             <h2 className="text-4xl font-bold text-[#163A6B]">
//               Ask me anything about the NED Prospectus
//             </h2>

//             <p className="mt-3 max-w-xl text-lg leading-8 text-slate-500">
//               Ask about admissions, eligibility, fees,
//               programmes, deadlines and official
//               prospectus information.
//             </p>
//           </div>

//           <ExampleChips
//             onSelect={handleSend}
//             disabled={isLoading}
//           />
//         </div>
//       )}

//       {!isLoadingHistory &&
//         messages.map((message) => (
//           <MessageBubble
//             key={message.id}
//             message={message}
//           />
//         ))}

//       {isLoading && (
//         <div className="flex items-start gap-3 animate-fade-in-up">
//           {/* AI Avatar */}
//           <div className="mt-1 flex h-10 w-10 items-center justify-center rounded-full bg-[#163A6B] text-white font-bold shadow-md">
//             AI
//           </div>

//           {/* Typing Bubble */}
//           <div className="flex items-center gap-2 rounded-3xl rounded-tl-md border border-slate-200 bg-white px-5 py-4 shadow-md">
//             <span
//               className="typing-dot h-2 w-2 rounded-full bg-[#163A6B]"
//               style={{ animationDelay: "0ms" }}
//             />
//             <span
//               className="typing-dot h-2 w-2 rounded-full bg-[#163A6B]"
//               style={{ animationDelay: "150ms" }}
//             />
//             <span
//               className="typing-dot h-2 w-2 rounded-full bg-[#163A6B]"
//               style={{ animationDelay: "300ms" }}
//             />
//           </div>
//         </div>
//       )}
//     </div>

//     {/* <div className="mt-4 shrink-0 border-t border-slate-200 bg-white pt-4">
//       <ChatInput
//         onSend={handleSend}
//         isLoading={isLoading || isLoadingHistory}
//       /> */}

//       <div className="mt-4 shrink-0 border-t border-slate-200 bg-white pt-4">
//         <div className="mb-3 flex justify-end">
//           <button
//             type="button"
//             onClick={onNewChat}
//             disabled={isLoading}
//             className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
//           >
//             New Chat
//           </button>
//         </div>

//         <ChatInput
//           onSend={handleSend}
//           isLoading={isLoading || isLoadingHistory}
//         />

//       <p className="mt-2 pb-1 text-center text-[11px] text-slate-400">
//         ProspectusAI may make mistakes. Please verify important information
//         with the official NED prospectus.
//       </p>
//     </div>
//   </div>
// );
// }