export type ChatStatus = "answered" | "needs_page_review";

export interface ChatSource {
  document: string;
  page_number: number;
  heading: string;
  score: number;
}

export interface PageReference {
  document: string;
  page_number: number;
  page_path: string | null;
  page_url: string;
  reason: string;
}

export interface ChatRequest {
  question: string;
}

export interface ChatResponse {
  answer: string;
  status: ChatStatus;
  sources: ChatSource[];
  page_references: PageReference[];
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
