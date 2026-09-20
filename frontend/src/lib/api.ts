import { getAccessToken, refreshSession, signOut } from "./supabase";
import { mockRequest } from "./mock";
import { ApiError } from "./errors";
import type { Attachment, AttachmentKind } from "./types";

// Pages import the error class from here (`import { ApiError } from "@/lib/api"`); it lives in ./errors.
export { ApiError } from "./errors";

/** True when there is no real backend (VITE_API_URL empty or "mock"): every call is answered by lib/mock.ts. */
export function isMock(): boolean {
  const url = import.meta.env.VITE_API_URL;
  return !url || url === "mock";
}

const REQUEST_TIMEOUT_MS = 60_000; // first request after idle can be slow on free hosting (docs/api.md 7.5)

/** X-Request-ID: [A-Za-z0-9-], at most 64 chars. crypto.randomUUID is missing on non-secure origins, so fall back. */
function generateRequestId(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  const bytes = new Uint8Array(16);
  if (c && typeof c.getRandomValues === "function") c.getRandomValues(bytes);
  else for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function getUrl(path: string): string {
  // Accept VITE_API_URL with or without a trailing slash or the /api/v1 suffix.
  const base = String(import.meta.env.VITE_API_URL).replace(/\/+$/, "").replace(/\/api\/v1$/, "");
  return `${base}/api/v1${path.startsWith("/") ? path : `/${path}`}`;
}

// ---------------------------------------------------------------------------
// Query strings
// ---------------------------------------------------------------------------
export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | QueryValue[]>;

/**
 * Build "?a=1&b=2" from an object. null / undefined / "" are skipped, arrays repeat the key
 * (`{ status: ["registered", "assessment"] }` -> `status=registered&status=assessment`), values are encoded.
 */
export function buildQuery(params?: QueryParams): string {
  if (!params) return "";
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    for (const v of Array.isArray(value) ? value : [value]) {
      if (v !== null && v !== undefined && v !== "") search.append(key, String(v));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

function withQuery(path: string, params?: QueryParams): string {
  const query = buildQuery(params);
  if (!query) return path;
  return path.includes("?") ? `${path}&${query.slice(1)}` : `${path}${query}`;
}

// ---------------------------------------------------------------------------
// Transport
// ---------------------------------------------------------------------------
function networkError(cause: unknown, timedOut: boolean): ApiError {
  if (timedOut || (cause instanceof DOMException && cause.name === "AbortError")) {
    return new ApiError(
      0,
      { error: { code: "timeout", message: "The server took too long to respond. Please try again." } },
    );
  }
  return new ApiError(
    0,
    { error: { code: "network_error", message: "We could not reach the server. Check your internet connection and try again." } },
  );
}

async function peekErrorCode(response: Response): Promise<string> {
  try {
    const body: unknown = await response.clone().json();
    const code = (body as { error?: { code?: unknown } } | null)?.error?.code;
    return typeof code === "string" ? code : "";
  } catch {
    return "";
  }
}

/**
 * One HTTP call with auth, X-Request-ID, a 60 s timeout and the 401 rules from docs/api.md 7.1:
 *  - token_expired            -> refresh the Supabase session and retry once
 *  - token_invalid            -> sign out
 *  - any other 401 with a token -> refresh and retry once; a second 401 signs out
 *  - 401 with no token (never signed in) -> just an error, nothing to sign out of
 *  - 403 is NEVER a reason to sign out (it means "signed in, but not allowed"), so it cannot cause a loop.
 */
async function send(url: string, init: RequestInit, retried = false): Promise<Response> {
  let token: string | null = null;
  try {
    token = await getAccessToken();
  } catch {
    token = null; // unreadable session: send the call without a token and let the server answer 401
  }

  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  headers.set("X-Request-ID", generateRequestId());

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  let response: Response;
  try {
    response = await fetch(url, { ...init, headers, signal: controller.signal });
  } catch (cause) {
    throw networkError(cause, controller.signal.aborted);
  } finally {
    clearTimeout(timeoutId);
  }

  if (response.status === 401 && token) {
    const code = await peekErrorCode(response);
    if (code === "token_invalid") {
      await signOut();
    } else if (!retried && (await refreshSession())) {
      return send(url, init, true);
    } else {
      await signOut();
    }
  }
  return response;
}

function statusFallback(status: number): { code: string; message: string } {
  if (status === 502 || status === 503 || status === 504) {
    return { code: "upstream_error", message: "The service is temporarily unavailable. Please try again in a moment." };
  }
  if (status >= 500) return { code: "internal_error", message: "Something went wrong on our side. Please try again." };
  if (status === 401) return { code: "unauthenticated", message: "Please sign in to continue." };
  if (status === 403) return { code: "forbidden", message: "You do not have access to this." };
  if (status === 404) return { code: "not_found", message: "That was not found." };
  return { code: "bad_request", message: `The request could not be completed (HTTP ${status}).` };
}

async function readBody<T>(response: Response): Promise<T> {
  if (response.status === 204 || response.status === 205) return undefined as T;
  const text = await response.text().catch(() => "");

  if (!response.ok) {
    let parsed: unknown = null;
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch {
      parsed = null; // e.g. an HTML error page from a proxy
    }
    const hasEnvelope = typeof parsed === "object" && parsed !== null && "error" in parsed;
    const fallback = statusFallback(response.status);
    const headerRetry = Number(response.headers.get("Retry-After"));
    const error = ApiError.fromResponse(
      response.status,
      hasEnvelope ? parsed : { error: { ...fallback } },
      response.headers.get("X-Request-ID") ?? "",
      Number.isFinite(headerRetry) && headerRetry > 0 ? headerRetry : null,
    );
    throw error;
  }

  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(response.status, {
      error: {
        code: "bad_response",
        message: "The server sent a reply we could not read. Please try again.",
        request_id: response.headers.get("X-Request-ID") ?? "",
      },
    });
  }
}

async function request<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  if (isMock()) return mockRequest<T>(method, path, form ?? body);

  const init: RequestInit = { method };
  if (form) {
    // FormData: the browser sets the multipart Content-Type with its boundary. Never set it by hand.
    init.body = form;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers = { "Content-Type": "application/json; charset=utf-8" };
  }
  const response = await send(getUrl(path), init);
  return readBody<T>(response);
}

// ---------------------------------------------------------------------------
// Public API. Paths are relative to /api/v1 (e.g. "/claims"); this module adds the prefix.
// ---------------------------------------------------------------------------

/** GET. List endpoints resolve to a Page<T> ({ items, total, limit, offset }); pass query values as `params`. */
export async function get<T>(path: string, params?: QueryParams): Promise<T> {
  return request<T>("GET", withQuery(path, params));
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

export async function patch<T>(path: string, body: unknown): Promise<T> {
  return request<T>("PATCH", path, body);
}

export async function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>("PUT", path, body);
}

/** GET a file (CSV, PDF) as a Blob, with the same auth and error handling as every other call. */
export async function getBlob(path: string): Promise<Blob> {
  if (isMock()) {
    throw new ApiError(0, { error: { code: "not_supported", message: "Downloads need the real backend." } });
  }
  const response = await send(getUrl(path), { method: "GET" });
  if (!response.ok) await readBody(response); // throws the ApiError
  return response.blob();
}

/** Download a file from the API through the browser (the auth header means a plain link would not work). */
export async function download(path: string, filename: string): Promise<void> {
  const blob = await getBlob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

/** DELETE. The API answers 204 with an empty body. */
export async function del(path: string): Promise<void> {
  await request<void>("DELETE", path);
}

/** POST multipart/form-data. Do not set a Content-Type; see uploadAttachment for the common case. */
export async function postForm<T>(path: string, formData: FormData): Promise<T> {
  return request<T>("POST", path, undefined, formData);
}

/**
 * Upload ONE file to `/claims/{id}/attachments` or `/requests/{id}/attachments`.
 * The API needs the parts `file`, `kind` (an AttachmentKind) and optionally `label` (max 120 chars).
 * Errors: 413 payload_too_large, 415 unsupported_media_type, 422 validation_error (attachment count limit).
 */
export async function uploadAttachment(
  path: string,
  file: File | Blob,
  options: { kind: AttachmentKind; label?: string | null; filename?: string },
): Promise<Attachment> {
  const form = new FormData();
  const name = options.filename ?? (file instanceof File ? file.name : "upload");
  form.append("file", file, name);
  form.append("kind", options.kind);
  if (options.label) form.append("label", options.label);
  return postForm<Attachment>(path, form);
}

// Convenience namespace — pages may import { api } or the named functions
export const api = { get, post, patch, put, del, postForm, upload: uploadAttachment };
