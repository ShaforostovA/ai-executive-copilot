import type {
  Digest,
  ErrorResponse,
  LoginCredentials,
  Principal,
  SourceDetail,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-Request-ID": crypto.randomUUID(),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let payload: ErrorResponse | undefined;
    try {
      payload = (await response.json()) as ErrorResponse;
    } catch {
      payload = undefined;
    }
    throw new ApiError(
      payload?.error.message ?? "Сервис временно недоступен.",
      response.status,
      payload?.error.code ?? "http_error",
      payload?.error.request_id ?? response.headers.get("X-Request-ID") ?? undefined,
    );
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  me: () => request<Principal>("/api/v1/auth/me"),
  login: (credentials: LoginCredentials) =>
    request<Principal>("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(credentials),
    }),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  dashboard: () => request<Digest>("/api/v1/dashboard"),
  source: (sourceId: string) => request<SourceDetail>(`/api/v1/sources/${sourceId}`),
};
