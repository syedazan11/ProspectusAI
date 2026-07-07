import { apiRequest } from "./api";
import type { ChatRequest, ChatResponse } from "../types/chat";

/**
 * Sends a question to the RAG chatbot backend.
 * POST /api/v1/chat
 */
export async function sendChatMessage(question: string): Promise<ChatResponse> {
  const payload: ChatRequest = { question };
  return apiRequest<ChatResponse>("/api/v1/chat", {
    method: "POST",
    body: payload,
  });
}

/**
 * Returns the direct URL for a given document page, for use with
 * GET /api/v1/pages/{document}/{page_number}. Prefer using the
 * page_url the backend already returns in page_references; this is a
 * fallback for constructing one manually if ever needed.
 */
export function pagePath(document: string, pageNumber: number): string {
  return `/api/v1/pages/${encodeURIComponent(document)}/${pageNumber}`;
}
