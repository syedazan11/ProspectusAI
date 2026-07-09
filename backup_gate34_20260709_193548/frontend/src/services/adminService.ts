import { API_BASE_URL, ApiError } from "./api";

const SESSION_KEY = "prospectusai_admin_session";

export interface AdminSession {
  id: string;
  username: string;
  password: string;
}

export interface AdminAccount {
  id: string;
  username: string;
}

export interface AdminListResult {
  admins: AdminAccount[];
  current_admin_id: string;
  maximum_admins: number;
}


export interface UploadResult {
  message: string;
  uploaded_by: string;
  document: Record<string, unknown>;
  result: Record<string, unknown>;
}

function authHeader(
  username: string,
  password: string,
): string {
  return `Basic ${btoa(
    unescape(
      encodeURIComponent(
        `${username}:${password}`,
      ),
    ),
  )}`;
}

async function errorMessage(
  response: Response,
): Promise<string> {
  try {
    const body = await response.json();
    return body.detail || body.message ||
      `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

export function getStoredSession():
  AdminSession | null {
  const raw = sessionStorage.getItem(
    SESSION_KEY,
  );

  if (!raw) return null;

  try {
    return JSON.parse(raw) as AdminSession;
  } catch {
    return null;
  }
}

export function storeSession(
  session: AdminSession,
): void {
  sessionStorage.setItem(
    SESSION_KEY,
    JSON.stringify(session),
  );
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

export async function loginAdmin(
  username: string,
  password: string,
): Promise<AdminSession> {
  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/admin/me`,
      {
        headers: {
          Authorization: authHeader(
            username,
            password,
          ),
        },
      },
    );
  } catch {
    throw new ApiError(
      "Could not reach the ProspectusAI server.",
    );
  }

  if (!response.ok) {
    throw new ApiError(
      await errorMessage(response),
      response.status,
    );
  }

  const admin = await response.json();

  const session: AdminSession = {
    id: admin.id,
    username: admin.username,
    password,
  };

  storeSession(session);

  return session;
}

export async function uploadProspectus(
  file: File,
  year: number,
  officialUrl: string,
  session: AdminSession,
): Promise<UploadResult> {
  const formData = new FormData();

  formData.append("file", file);
  formData.append("year", String(year));
  formData.append(
    "official_url",
    officialUrl,
  );

  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}/api/v1/admin/documents/upload`,
      {
        method: "POST",
        headers: {
          Authorization: authHeader(
            session.username,
            session.password,
          ),
        },
        body: formData,
      },
    );
  } catch {
    throw new ApiError(
      "Could not reach the ProspectusAI server.",
    );
  }

  if (!response.ok) {
    throw new ApiError(
      await errorMessage(response),
      response.status,
    );
  }

  return response.json();
}


export async function listAdmins(
  session: AdminSession,
): Promise<AdminListResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/admins`,
    {
      headers: {
        Authorization: authHeader(
          session.username,
          session.password,
        ),
      },
    },
  );

  if (!response.ok) {
    throw new ApiError(
      await errorMessage(response),
      response.status,
    );
  }

  return response.json();
}

export async function createAdmin(
  username: string,
  password: string,
  session: AdminSession,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/admins`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authHeader(
          session.username,
          session.password,
        ),
      },
      body: JSON.stringify({
        username,
        password,
      }),
    },
  );

  if (!response.ok) {
    throw new ApiError(
      await errorMessage(response),
      response.status,
    );
  }
}

export async function deleteAdmin(
  adminId: string,
  session: AdminSession,
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/admin/admins/${encodeURIComponent(
      adminId,
    )}`,
    {
      method: "DELETE",
      headers: {
        Authorization: authHeader(
          session.username,
          session.password,
        ),
      },
    },
  );

  if (!response.ok) {
    throw new ApiError(
      await errorMessage(response),
      response.status,
    );
  }
}
