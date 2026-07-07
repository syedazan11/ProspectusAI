// Types for the (currently mocked / not-yet-built) admin backend.
// Keep these aligned with the planned endpoints so swapping the mock
// for a real API later is a drop-in change.

export interface AdminLoginRequest {
  username: string;
  password: string;
}

export interface AdminLoginResponse {
  token: string;
  username: string;
}

export type ProcessingStage =
  | "Uploaded"
  | "Parsing"
  | "Extracting tables"
  | "Building chunks"
  | "Building graph"
  | "Indexing"
  | "Ready";

export const PROCESSING_STAGES: ProcessingStage[] = [
  "Uploaded",
  "Parsing",
  "Extracting tables",
  "Building chunks",
  "Building graph",
  "Indexing",
  "Ready",
];

export interface ProcessingSummary {
  total_pages: number;
  processed_pages: number;
  failed_pages: number;
  quarantined_pages: number;
}

export interface ProspectusDocument {
  document_id: string;
  name: string;
  uploaded_at: string;
  stage: ProcessingStage;
  summary: ProcessingSummary | null;
}

export interface ProcessingStatusResponse {
  document_id: string;
  stage: ProcessingStage;
  summary: ProcessingSummary;
}

/** Generic wrapper so the UI can tell a real response apart from a
 * "this backend route doesn't exist yet" placeholder result. */
export interface BackendCallResult<T> {
  ok: boolean;
  connected: boolean;
  data: T | null;
  error?: string;
}
