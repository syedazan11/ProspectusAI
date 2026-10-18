export type ChatStatus =
  | "answered"
  | "needs_page_review"
  | "seat_distribution_pages";

export interface ChatSource {
  document: string;
  page_number: number;
  heading: string;
  score?: number | null;
}

export interface PageReference {
  document: string;
  // page_number: number;
  page_number: number | null;
  page_path?: string | null;
  page_url?: string | null;
  reason?: string | null;
}

// export interface ChatSummary {
//   id: string;
//   title: string;
//   created_at: string;
//   updated_at: string;
// }

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[];
  page_references: PageReference[];
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  status?: ChatStatus;
  sources?: ChatSource[];
  pageReferences?: PageReference[];
  isError?: boolean;
  createdAt: number;
}

// export interface ChatListResponse {
//   chats: ChatSummary[];
// }

export interface ChatMessagesResponse {
  messages: StoredMessage[];
}

export interface SendMessageResponse {
  answer: string;
  status: ChatStatus;
  sources: ChatSource[];
  page_references: PageReference[];
  message: StoredMessage;
}
