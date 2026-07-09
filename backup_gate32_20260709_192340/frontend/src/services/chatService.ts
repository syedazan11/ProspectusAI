import { API_BASE_URL, ApiError, apiRequest } from "./api";
import type {
  ChatListResponse,
  ChatMessagesResponse,
  ChatSummary,
  SendMessageResponse,
} from "../types/chat";

const OWNER_ID_KEY =
  "prospectusai_chat_owner_id";

export function getChatOwnerId(): string {
  const existing =
    localStorage.getItem(OWNER_ID_KEY);

  if (existing) {
    return existing;
  }

  const ownerId = crypto.randomUUID();

  localStorage.setItem(
    OWNER_ID_KEY,
    ownerId,
  );

  return ownerId;
}

function ownerHeaders(): Record<string, string> {
  return {
    "X-Chat-Owner-ID": getChatOwnerId(),
  };
}

export async function listChats(): Promise<
  ChatSummary[]
> {
  const response =
    await apiRequest<ChatListResponse>(
      "/api/v1/chats",
      {
        headers: ownerHeaders(),
      },
    );

  return response.chats;
}

export async function createChat(): Promise<
  ChatSummary
> {
  return apiRequest<ChatSummary>(
    "/api/v1/chats",
    {
      method: "POST",
      headers: ownerHeaders(),
    },
  );
}

export async function getChatMessages(
  chatId: string,
): Promise<ChatMessagesResponse> {
  return apiRequest<ChatMessagesResponse>(
    `/api/v1/chats/${encodeURIComponent(
      chatId,
    )}/messages`,
    {
      headers: ownerHeaders(),
    },
  );
}

export async function sendChatMessage(
  chatId: string,
  question: string,
): Promise<SendMessageResponse> {
  return apiRequest<SendMessageResponse>(
    `/api/v1/chats/${encodeURIComponent(
      chatId,
    )}/messages`,
    {
      method: "POST",
      headers: ownerHeaders(),
      body: {
        question,
      },
    },
  );
}

export async function renameChat(
  chatId: string,
  title: string,
): Promise<void> {
  await apiRequest<void>(
    `/api/v1/chats/${encodeURIComponent(
      chatId,
    )}`,
    {
      method: "PATCH",
      headers: ownerHeaders(),
      body: {
        title,
      },
    },
  );
}

export async function deleteChat(
  chatId: string,
): Promise<void> {
  await apiRequest<void>(
    `/api/v1/chats/${encodeURIComponent(
      chatId,
    )}`,
    {
      method: "DELETE",
      headers: ownerHeaders(),
    },
  );
}


export interface ChatStreamHandlers {
  onToken: (token: string) => void;
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

  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/chats/${encodeURIComponent(
        chatId,
      )}/messages/stream`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...ownerHeaders(),
        },
        body: JSON.stringify({
          question,
        }),
      },
    );
  } catch {
    throw new ApiError(
      "Could not reach the ProspectusAI server. Please check your connection and try again.",
    );
  }

  if (!response.ok) {
    throw new ApiError(
      `Request failed with status ${response.status}`,
      response.status,
    );
  }

  if (!response.body) {
    throw new ApiError(
      "The server returned an empty stream.",
    );
  }

  const reader = response.body
    .pipeThrough(new TextDecoderStream())
    .getReader();

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
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
        handlers.onToken(event.content);
      } else if (event.type === "done") {
        handlers.onDone(event);
      } else if (event.type === "error") {
        throw new ApiError(
          event.message ||
            "Streaming failed.",
        );
      }
    }
  }
}
