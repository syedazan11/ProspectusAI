import { apiRequest, ApiError } from "./api";
import type {
  AdminLoginResponse,
  BackendCallResult,
  ProcessingStatusResponse,
  ProspectusDocument,
} from "../types/admin";

/* -------------------------------------------------------------------------
 * DEVELOPMENT-ONLY MOCK AUTH
 * -------------------------------------------------------------------------
 * The real admin backend (POST /api/v1/admin/login) is not built yet.
 * These fake credentials exist purely so the dashboard can be developed
 * and demoed locally. They are NOT real credentials, are never sent to
 * any server, and this whole block should be deleted once the real
 * /api/v1/admin/login endpoint exists (see loginAdmin below for the
 * real-endpoint call that is already wired up and ready to use instead).
 * ---------------------------------------------------------------------- */
const MOCK_ADMIN_USERNAME = "admin";
const MOCK_ADMIN_PASSWORD = "prospectus-dev-only";
const SESSION_KEY = "prospectusai_admin_session";

export interface AdminSession {
  username: string;
  token: string;
  mock: true;
}

export function mockLogin(
  username: string,
  password: string
): AdminSession | null {
  if (username === MOCK_ADMIN_USERNAME && password === MOCK_ADMIN_PASSWORD) {
    const session: AdminSession = {
      username,
      token: "mock-session-token",
      mock: true,
    };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    return session;
  }
  return null;
}

export function getStoredSession(): AdminSession | null {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AdminSession;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

/* -------------------------------------------------------------------------
 * REAL BACKEND CALLS (planned endpoints, not built yet)
 * -------------------------------------------------------------------------
 * These call the real routes and are ready to use as soon as the backend
 * team ships them. Each wraps failures into a BackendCallResult so the UI
 * can distinguish "endpoint doesn't exist / server unreachable" from a
 * genuine empty result, and show a "not connected yet" state instead of
 * crashing.
 * ---------------------------------------------------------------------- */

async function callOptionalEndpoint<T>(
  fn: () => Promise<T>
): Promise<BackendCallResult<T>> {
  try {
    const data = await fn();
    return { ok: true, connected: true, data };
  } catch (err) {
    const message = err instanceof ApiError ? err.message : "Unknown error";
    // 404 / network failure -> treat as "not connected yet" rather than a hard error
    const notConnected =
      err instanceof ApiError && (err.status === 404 || err.status === undefined);
    return {
      ok: false,
      connected: !notConnected,
      data: null,
      error: message,
    };
  }
}

/** POST /api/v1/admin/login (not built yet — safe to call, fails gracefully) */
export async function loginAdmin(
  username: string,
  password: string
): Promise<BackendCallResult<AdminLoginResponse>> {
  return callOptionalEndpoint(() =>
    apiRequest<AdminLoginResponse>("/api/v1/admin/login", {
      method: "POST",
      body: { username, password },
    })
  );
}

/** POST /api/v1/admin/upload (not built yet — safe to call, fails gracefully) */
export async function uploadProspectus(
  file: File
): Promise<BackendCallResult<{ document_id: string }>> {
  return callOptionalEndpoint(async () => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL}/api/v1/admin/upload`,
      { method: "POST", body: formData }
    );
    if (!response.ok) {
      throw new ApiError(`Upload failed with status ${response.status}`, response.status);
    }
    return response.json();
  });
}

/** GET /api/v1/admin/documents (not built yet — safe to call, fails gracefully) */
export async function fetchDocuments(): Promise<
  BackendCallResult<ProspectusDocument[]>
> {
  return callOptionalEndpoint(() =>
    apiRequest<ProspectusDocument[]>("/api/v1/admin/documents")
  );
}

/** GET /api/v1/admin/processing-status/{document_id} (not built yet) */
export async function fetchProcessingStatus(
  documentId: string
): Promise<BackendCallResult<ProcessingStatusResponse>> {
  return callOptionalEndpoint(() =>
    apiRequest<ProcessingStatusResponse>(
      `/api/v1/admin/processing-status/${encodeURIComponent(documentId)}`
    )
  );
}
