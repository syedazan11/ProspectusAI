export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

export class ApiError extends Error {
  status?: number;

  constructor(
    message: string,
    status?: number,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface RequestOptions {
  method?:
    | "GET"
    | "POST"
    | "PUT"
    | "PATCH"
    | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    method = "GET",
    body,
    headers = {},
  } = options;

  let response: Response;

  try {
    response = await fetch(
      `${API_BASE_URL}${path}`,
      {
        method,
        headers: {
          "Content-Type": "application/json",
          ...headers,
        },
        body:
          body !== undefined
            ? JSON.stringify(body)
            : undefined,
      },
    );
  } catch {
    throw new ApiError(
      "Could not reach the ProspectusAI server. " +
        "Please check your connection and try again.",
    );
  }

  if (!response.ok) {
    let message =
      `Request failed with status ${response.status}`;

    try {
      const errorBody = await response.json();

      if (
        typeof errorBody?.detail === "string"
      ) {
        message = errorBody.detail;
      } else if (
        typeof errorBody?.message === "string"
      ) {
        message = errorBody.message;
      }
    } catch {
      // Keep the default message.
    }

    throw new ApiError(
      message,
      response.status,
    );
  }

  const text = await response.text();

  if (!text) {
    return undefined as T;
  }

  return JSON.parse(text) as T;
}

export function buildPageUrl(
  pageUrl: string,
): string {
  if (/^https?:\/\//i.test(pageUrl)) {
    return pageUrl;
  }

  return (
    `${API_BASE_URL}` +
    `${pageUrl.startsWith("/") ? "" : "/"}` +
    pageUrl
  );
}
