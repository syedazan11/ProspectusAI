// import { API_BASE_URL, ApiError, apiRequest } from "./api";
// import type {
//   ChatListResponse,
//   ChatMessagesResponse,
//   ChatSummary,
//   SendMessageResponse,
// } from "../types/chat";

// // const OWNER_ID_KEY =
// //   "prospectusai_chat_owner_id";

// // export function getChatOwnerId(): string {
// //   const adminSession = sessionStorage.getItem(
// //     "prospectusai_admin_session",
// //   );

// //   if (adminSession) {
// //     try {
// //       const admin = JSON.parse(adminSession) as {
// //         id?: string;
// //       };

// //       if (admin.id) {
// //         return `admin:${admin.id}`;
// //       }
// //     } catch {
// //       // Fall back to the public browser owner.
// //     }
// //   }

// //   const existing =
// //     localStorage.getItem(OWNER_ID_KEY);

// //   if (existing) {
// //     return existing;
// //   }

// //   const ownerId = crypto.randomUUID();

// //   localStorage.setItem(
// //     OWNER_ID_KEY,
// //     ownerId,
// //   );

// //   return ownerId;
// // }

// // function ownerHeaders(): Record<string, string> {
// //   return {
// //     "X-Chat-Owner-ID": getChatOwnerId(),
// //   };
// // }

// // export async function listChats(): Promise<
// //   ChatSummary[]
// // > {
// //   const response =
// //     await apiRequest<ChatListResponse>(
// //       "/api/v1/chats",
// //       {
// //         headers: ownerHeaders(),
// //       },
// //     );

// //   return response.chats;
// // }

// // export async function createChat(): Promise<
// //   ChatSummary
// // > {
// //   return apiRequest<ChatSummary>(
// //     "/api/v1/chats",
// //     {
// //       method: "POST",
// //       headers: ownerHeaders(),
// //     },
// //   );
// // }

// // export async function createChat(): Promise<
// //   ChatSummary
// // > {
// //   const start = performance.now();

// //   console.log(
// //     "[CREATE CHAT TIMING] START",
// //   );

// //   const result = await apiRequest<ChatSummary>(
// //     "/api/v1/chats",
// //     {
// //       method: "POST",
// //       headers: ownerHeaders(),
// //     },
// //   );

// //   console.log(
// //     `[CREATE CHAT TIMING] END: ${
// //       performance.now() - start
// //     }ms`,
// //   );

// //   return result;
// // }

// // export async function getChatMessages(
// //   chatId: string,
// // ): Promise<ChatMessagesResponse> {
// //   return apiRequest<ChatMessagesResponse>(
// //     `/api/v1/chats/${encodeURIComponent(
// //       chatId,
// //     )}/messages`,
// //     {
// //       headers: ownerHeaders(),
// //     },
// //   );
// // }

// // export async function sendChatMessage(
// //   chatId: string,
// //   question: string,
// // ): Promise<SendMessageResponse> {
// //   return apiRequest<SendMessageResponse>(
// //     `/api/v1/chats/${encodeURIComponent(
// //       chatId,
// //     )}/messages`,
// //     {
// //       method: "POST",
// //       headers: ownerHeaders(),
// //       body: {
// //         question,
// //       },
// //     },
// //   );
// // }

// // export async function renameChat(
// //   chatId: string,
// //   title: string,
// // ): Promise<void> {
// //   await apiRequest<void>(
// //     `/api/v1/chats/${encodeURIComponent(
// //       chatId,
// //     )}`,
// //     {
// //       method: "PATCH",
// //       headers: ownerHeaders(),
// //       body: {
// //         title,
// //       },
// //     },
// //   );
// // }

// // export async function deleteChat(
// //   chatId: string,
// // ): Promise<void> {
// //   await apiRequest<void>(
// //     `/api/v1/chats/${encodeURIComponent(
// //       chatId,
// //     )}`,
// //     {
// //       method: "DELETE",
// //       headers: ownerHeaders(),
// //     },
// //   );
// // }


// export interface ChatStreamHandlers {
//   onToken: (token: string) => void;
//   onReplace: (content: string) => void;
//   onDone: (
//     response: SendMessageResponse,
//   ) => void;
// }

// // export async function streamChatMessage(
// //   chatId: string,
// //   question: string,
// //   handlers: ChatStreamHandlers,
// // ): Promise<void> {
// //   let response: Response;

// //   const streamStart = performance.now();

// //   console.log(
// //     "[STREAM TIMING] START",
// //   );

// //   try {
// //     response = await fetch(
// //       `${API_BASE_URL}/api/v1/chats/${encodeURIComponent(
// //         chatId,
// //       )}/messages/stream`,
// //       {
// //         method: "POST",
// //         headers: {
// //           "Content-Type": "application/json",
// //           ...ownerHeaders(),
// //         },
// //         body: JSON.stringify({
// //           question,
// //         }),
// //       },
// //     );
// //     console.log(
// //       `[STREAM TIMING] FETCH RESPONSE: ${
// //         performance.now() - streamStart
// //       }ms`,
// //     );
// //   } catch {
// //     throw new ApiError(
// //       "Could not reach the ProspectusAI server. Please check your connection and try again.",
// //     );
// //   }

// //   if (!response.ok) {
// //     throw new ApiError(
// //       `Request failed with status ${response.status}`,
// //       response.status,
// //     );
// //   }

// //   if (!response.body) {
// //     throw new ApiError(
// //       "The server returned an empty stream.",
// //     );
// //   }

// //   const reader = response.body
// //     .pipeThrough(new TextDecoderStream())
// //     .getReader();

// //   console.log(
// //     `[STREAM TIMING] READER CREATED: ${
// //       performance.now() - streamStart
// //     }ms`,
// //   );

// //   let buffer = "";
// //   let firstChunk = false;
// //   let firstToken = false;

// //   while (true) {
// //     const { value, done } = await reader.read();

// //     if (done) {
// //       break;
// //     }

// //     if (!firstChunk) {
// //       firstChunk = true;

// //       console.log(
// //         `[STREAM TIMING] FIRST CHUNK: ${
// //           performance.now() - streamStart
// //         }ms`,
// //       );
// //     }

// //     buffer += value;

// //     const lines = buffer.split("\n");
// //     buffer = lines.pop() ?? "";

// //     for (const line of lines) {
// //       if (!line.trim()) {
// //         continue;
// //       }

// //       const event = JSON.parse(line);

// //       if (event.type === "token") {
// //         if (!firstToken) {
// //           firstToken = true;

// //           console.log(
// //             `[STREAM TIMING] FIRST TOKEN: ${
// //               performance.now() - streamStart
// //             }ms`,
// //           );
// //         }

// //         handlers.onToken(event.content);
// //       } else if (event.type === "replace") {
// //         handlers.onReplace(event.content);
// //       } else if (event.type === "done") {
// //         handlers.onDone(event);
// //       } else if (event.type === "error") {
// //         throw new ApiError(
// //           event.message ||
// //             "Streaming failed.",
// //         );
// //       }
// //     }
// //   }
// //   console.log(
// //     `[STREAM TIMING] END: ${
// //       performance.now() - streamStart
// //     }ms`,
// //   );
// // }

import { API_BASE_URL, ApiError, apiRequest } from "./api";
import type {
  ChatMessagesResponse,
  SendMessageResponse,
} from "../types/chat";

export async function getChatMessages(
  chatId: string,
): Promise<ChatMessagesResponse> {
  return apiRequest<ChatMessagesResponse>(
    `/api/v1/chats/${encodeURIComponent(chatId)}/messages`,
  );
}

export interface ChatStreamHandlers {
  onToken: (token: string) => void;
  onReplace: (content: string) => void;
  onDone: (
    response: SendMessageResponse,
  ) => void;
}

export async function streamChatMessage(
  chatId: string,
  question: string,
  handlers: ChatStreamHandlers,
): Promise<void> {
  let response: Response;

  const streamStart = performance.now();

  console.log("[STREAM TIMING] START");

  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/chats/${encodeURIComponent(
        chatId,
      )}/messages/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question,
        }),
      },
    );

    console.log(
      `[STREAM TIMING] FETCH RESPONSE: ${
        performance.now() - streamStart
      }ms`,
    );
  // } catch {
  //   throw new ApiError(
  //     "Could not reach the ProspectusAI server. Please check your connection and try again.",
  //   );
  // }

  } catch (error) {
    console.error("[STREAM FETCH ERROR]", error);

    throw new ApiError(
      error instanceof Error
        ? `Request failed: ${error.message}`
        : "Could not reach the ProspectusAI server. Please check your connection and try again.",
    );
  }

  // if (!response.ok) {
  //   throw new ApiError(
  //     `Request failed with status ${response.status}`,
  //     response.status,
  //   );
  // }
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();
      message =
        errorData.detail ||
        errorData.message ||
        errorData.error ||
        message;
    } catch {
      // Keep the fallback message if the response isn't JSON.
    }

    throw new ApiError(message, response.status);
  }

  if (!response.body) {
    throw new ApiError(
      "The server returned an empty stream.",
    );
  }

  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .getReader();

  console.log(
    `[STREAM TIMING] READER CREATED: ${
      performance.now() - streamStart
    }ms`,
  );

  let buffer = "";
  let firstChunk = false;
  let firstToken = false;

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    if (!firstChunk) {
      firstChunk = true;

      console.log(
        `[STREAM TIMING] FIRST CHUNK: ${
          performance.now() - streamStart
        }ms`,
      );
    }

    buffer += value;

    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.trim()) {
        continue;
      }

      const event = JSON.parse(line);

      if (event.type === "token") {
        if (!firstToken) {
          firstToken = true;

          console.log(
            `[STREAM TIMING] FIRST TOKEN: ${
              performance.now() - streamStart
            }ms`,
          );
        }

        handlers.onToken(event.content);
      } else if (event.type === "replace") {
        handlers.onReplace(event.content);
      } else if (event.type === "done") {
        handlers.onDone(event);
      } else if (event.type === "error") {
        throw new ApiError(
          event.message || "Streaming failed.",
        );
      }
    }
  }

  console.log(
    `[STREAM TIMING] END: ${
      performance.now() - streamStart
    }ms`,
  );
}