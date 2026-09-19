import type { FieldError } from "./types";

/**
 * Error thrown by every call in lib/api.ts. It carries the backend envelope
 * (docs/api.md 1.4): `{ error: { code, message, details[], request_id, retry_after_seconds } }`.
 *
 * `status` is 0 when the request never got an HTTP answer (offline, CORS, timeout);
 * `code` is then "network_error" or "timeout".
 */
export class ApiError extends Error {
  public readonly status: number;
  /** Machine-readable code (docs/api.md 1.4). Branch on this, never on `message`. */
  public readonly code: string;
  /** Field-level problems (validation_error only). Always an array, empty when none. */
  public readonly details: FieldError[];
  /** Server request id ("" when unknown). Show it in a "copy details" affordance. */
  public readonly requestId: string;
  /** Seconds to wait (rate_limited / llm_unavailable only). */
  public readonly retryAfterSeconds: number | null;

  constructor(status: number, body?: unknown, fallbackMessage?: string) {
    const env = readEnvelope(body);
    super(env.message || fallbackMessage || "Unknown API Error");
    this.name = "ApiError";
    this.status = status;
    this.code = env.code || "unknown";
    this.details = env.details;
    this.requestId = env.requestId;
    this.retryAfterSeconds = env.retryAfterSeconds;
  }

  /** Build from an HTTP error response; fills request id / retry-after from the headers when the body lacks them. */
  static fromResponse(
    status: number,
    body: unknown,
    headerRequestId = "",
    headerRetryAfter: number | null = null,
  ): ApiError {
    const env = readEnvelope(body);
    return new ApiError(status, {
      error: {
        code: env.code,
        message: env.message,
        details: env.details,
        request_id: env.requestId || headerRequestId,
        retry_after_seconds: env.retryAfterSeconds ?? headerRetryAfter,
      },
    });
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

interface Envelope {
  code: string;
  message: string;
  details: FieldError[];
  requestId: string;
  retryAfterSeconds: number | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readEnvelope(body: unknown): Envelope {
  const inner = isRecord(body) && isRecord(body.error) ? body.error : {};
  const rawDetails = Array.isArray(inner.details) ? inner.details : [];
  const details: FieldError[] = rawDetails
    .filter(isRecord)
    .map((d) => ({
      field: typeof d.field === "string" ? d.field : "",
      code: typeof d.code === "string" ? d.code : "invalid",
      message: typeof d.message === "string" ? d.message : "Invalid value.",
    }));
  const retry = inner.retry_after_seconds;
  return {
    code: typeof inner.code === "string" ? inner.code : "",
    message: typeof inner.message === "string" ? inner.message : "",
    details,
    requestId: typeof inner.request_id === "string" ? inner.request_id : "",
    retryAfterSeconds: typeof retry === "number" && Number.isFinite(retry) ? retry : null,
  };
}

/**
 * Map of field path -> first message, for showing validation errors next to inputs.
 * Paths are exactly the backend's, e.g. "incident.description", "witnesses[0].phone",
 * "payload.postal_code". Pass `stripPrefix: "payload."` to get bare field names.
 */
export function fieldErrorMap(error: unknown, stripPrefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  if (!isApiError(error)) return out;
  for (const d of error.details) {
    const key = stripPrefix && d.field.startsWith(stripPrefix) ? d.field.slice(stripPrefix.length) : d.field;
    if (key && !(key in out)) out[key] = d.message;
  }
  return out;
}

/** What the UI shows for an error. Never contains "[object Object]" or a raw stack. */
export interface ErrorInfo {
  title: string;
  message: string;
  code: string | null;
  status: number | null;
  requestId: string | null;
  details: FieldError[];
  retryAfterSeconds: number | null;
  /** True when trying again later can help (network, 5xx, 429, LLM unavailable). */
  retryable: boolean;
}

const GENERIC_MESSAGE = "Something went wrong. Please try again.";
const RUNTIME_ERROR_NAMES = new Set(["TypeError", "ReferenceError", "SyntaxError", "RangeError", "EvalError", "URIError"]);

function titleForStatus(status: number, code: string): string {
  if (code === "network_error") return "Can't reach the server";
  if (code === "timeout") return "The server took too long";
  if (code === "llm_unavailable") return "The assistant is unavailable";
  if (status === 401) return "Please sign in again";
  if (status === 403) return "Access denied";
  if (status === 404) return "Not found";
  if (status === 409) return "That can't be done right now";
  if (status === 413 || status === 415) return "That file can't be uploaded";
  if (status === 422) return "Please check the details";
  if (status === 429) return "Too many requests";
  if (status >= 500) return "Something went wrong";
  return "Something went wrong";
}

function messageForApiError(error: ApiError): string {
  // docs/api.md 1.4: 4xx messages are safe to show; for 5xx show our own generic text.
  if (error.status === 0) return error.message || GENERIC_MESSAGE;
  if (error.status >= 500 && error.code !== "llm_unavailable") {
    return error.code === "upstream_error" || error.status === 502 || error.status === 503 || error.status === 504
      ? "A service we depend on is not responding right now. Please try again in a moment."
      : "Something went wrong on our side. Please try again in a moment.";
  }
  if (error.code === "llm_unavailable" || error.code === "rate_limited") {
    const wait = error.retryAfterSeconds;
    const base = error.code === "rate_limited" ? "You are sending requests too quickly." : "The assistant is busy right now.";
    return wait ? `${base} Please try again in about ${wait} seconds.` : `${base} Please try again shortly.`;
  }
  return error.message || GENERIC_MESSAGE;
}

/** Turn anything thrown (ApiError, Error, string, raw envelope, object) into displayable text. */
export function describeError(error: unknown): ErrorInfo {
  if (isApiError(error)) {
    const retryable =
      error.status === 0 || error.status >= 500 || error.status === 429 || error.code === "llm_unavailable";
    return {
      title: titleForStatus(error.status, error.code),
      message: messageForApiError(error),
      code: error.code,
      status: error.status,
      requestId: error.requestId || null,
      details: error.details,
      retryAfterSeconds: error.retryAfterSeconds,
      retryable,
    };
  }

  const base: ErrorInfo = {
    title: "Something went wrong",
    message: GENERIC_MESSAGE,
    code: null,
    status: null,
    requestId: null,
    details: [],
    retryAfterSeconds: null,
    retryable: true,
  };

  if (typeof error === "string" && error.trim()) return { ...base, message: error.trim() };

  if (error instanceof Error) {
    // A page bug (TypeError etc.) is not something to show a client; a deliberate Error("...") is.
    return RUNTIME_ERROR_NAMES.has(error.name) || !error.message ? base : { ...base, message: error.message };
  }

  if (isRecord(error)) {
    // A raw backend envelope someone stored, or a { message } object.
    if (isRecord(error.error)) {
      const env = readEnvelope(error);
      return {
        ...base,
        message: env.message || base.message,
        code: env.code || null,
        requestId: env.requestId || null,
        details: env.details,
        retryAfterSeconds: env.retryAfterSeconds,
      };
    }
    if (typeof error.message === "string" && error.message.trim()) return { ...base, message: error.message.trim() };
  }

  return base;
}

/** Just the text, for toasts and inline messages. */
export function errorMessage(error: unknown): string {
  return describeError(error).message;
}

/**
 * Friendly text for a failed supabase.auth call (sign in). Works on the error's shape so it does not
 * depend on which supabase-js error class was thrown.
 */
export function friendlyAuthError(error: unknown): string {
  const e = isRecord(error) ? error : {};
  const name = typeof e.name === "string" ? e.name : "";
  const code = typeof e.code === "string" ? e.code : "";
  const message = typeof e.message === "string" ? e.message : error instanceof Error ? error.message : "";
  const status = typeof e.status === "number" ? e.status : undefined;

  if (code === "invalid_credentials" || /invalid login credentials/i.test(message)) {
    return "That email or password is not correct. Please check them and try again.";
  }
  if (code === "email_not_confirmed" || /email not confirmed/i.test(message)) {
    return "Your email address has not been confirmed yet. Check your inbox for the confirmation link.";
  }
  if (code === "user_banned") {
    return "This account has been disabled. Please contact your adviser.";
  }
  if (status === 429 || /rate limit|too many/i.test(message) || code === "over_request_rate_limit") {
    return "Too many sign-in attempts. Please wait a minute and try again.";
  }
  if (
    name === "AuthRetryableFetchError" ||
    error instanceof TypeError ||
    /failed to fetch|network|load failed|fetch/i.test(message) ||
    (status !== undefined && (status === 0 || status >= 500))
  ) {
    return "We could not reach the sign-in service. Check your internet connection and try again.";
  }
  return "We could not sign you in. Please try again.";
}
