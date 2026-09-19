import { getAccessToken, supabase, signOut } from "./supabase";
import { mockHandlers } from "./mock";

export class ApiError extends Error {
  public code: string;
  public details?: any[];
  public requestId: string;
  public retryAfterSeconds?: number | null;
  public status: number;

  constructor(status: number, errorBody: any) {
    super(errorBody?.error?.message || "Unknown API Error");
    this.name = "ApiError";
    this.status = status;
    this.code = errorBody?.error?.code || "unknown";
    this.details = errorBody?.error?.details;
    this.requestId = errorBody?.error?.request_id || "unknown";
    this.retryAfterSeconds = errorBody?.error?.retry_after_seconds;
  }
}

export function isMock(): boolean {
  const url = import.meta.env.VITE_API_URL;
  return !url || url === "mock";
}

function generateRequestId(): string {
  return crypto.randomUUID();
}

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  isRetry = false,
): Promise<Response> {
  let token = await getAccessToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  headers.set("X-Request-ID", generateRequestId());

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json; charset=utf-8");
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    if (response.status === 401 && !isRetry) {
      // Check if it's token_expired
      let errorBody;
      try {
        errorBody = await response.clone().json();
      } catch (e) {}

      if (errorBody?.error?.code === "token_expired") {
        const { error: refreshError } = await supabase.auth.refreshSession();
        if (!refreshError) {
          return fetchWithRetry(url, options, true);
        }
      } else if (errorBody?.error?.code === "token_invalid") {
        await signOut();
      } else {
        await signOut();
      }
    } else if (response.status === 401 && isRetry) {
      await signOut();
    }

    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return {} as T;
  if (!response.ok) {
    let errorBody;
    try {
      errorBody = await response.json();
    } catch (e) {
      errorBody = {
        error: {
          message: response.statusText,
          request_id: response.headers.get("X-Request-ID"),
        },
      };
    }
    throw new ApiError(response.status, errorBody);
  }
  return response.json() as Promise<T>;
}

async function mockFetch<T>(path: string, options: RequestInit): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, 200)); // 200ms delay

  // Clean path for exact match
  const base = path.split("?")[0];

  if (mockHandlers[base]) {
    return mockHandlers[base] as T;
  }

  // Fallback for paths with IDs e.g., /claims/123 -> returns the mock claim
  if (
    base.startsWith("/claims/") &&
    base !== "/claims/checklist" &&
    base !== "/claims/pipeline"
  ) {
    return {
      id: base.split("/")[2],
      reference: "CLM-MOCK",
      status: "assessment",
      status_label: "Assessment",
      client: {
        id: "0b7e3a52-1c4e-4c39-9e44-2a4f6e1b8a01",
        full_name: "Thabo Mokoena",
      },
      insurer: null,
      claim_number: null,
      incident_occurred_at: null,
      incident_location_text: null,
      hire_car_status: "not_required",
      days_in_status: 0,
      submitted_at: null,
      updated_at: new Date().toISOString(),
      policy_id: null,
      incident: {
        occurred_at: null,
        location_text: null,
        location_lat: null,
        location_lng: null,
        description: null,
      },
      police: {
        reported: null,
        case_number: null,
        station: null,
        reported_at: null,
        report_deadline_at: null,
        deadline_status: "not_applicable",
      },
      driver: {
        is_policyholder: null,
        full_name: null,
        relationship_to_policyholder: null,
      },
      vehicle_use: null,
      witnesses: [],
      third_parties: [],
      insurer_details: {
        claim_number: null,
        handler_name: null,
        handler_email: null,
        handler_phone: null,
      },
      repair: {
        repairer_name: null,
        repairer_phone: null,
        quote_amount_cents: null,
        authorised_amount_cents: null,
        drop_off_date: null,
        estimated_completion_date: null,
        completed_at: null,
      },
      hire_car: {
        status: "not_required",
        provider: null,
        delivery_date: null,
        return_date: null,
      },
      review: null,
      missing_fields: [],
      allowed_transitions: [],
      attachments: [],
      timeline: [],
      created_at: new Date().toISOString(),
      closed_at: null,
    } as unknown as T;
  }

  throw new ApiError(404, {
    error: { code: "not_found", message: "Mock not found", request_id: "mock" },
  });
}

function getUrl(path: string) {
  const baseUrl = import.meta.env.VITE_API_URL;
  return `${baseUrl}/api/v1${path}`;
}

export async function get<T>(path: string): Promise<T> {
  if (isMock()) return mockFetch<T>(path, { method: "GET" });
  const res = await fetchWithRetry(getUrl(path), { method: "GET" });
  return handleResponse<T>(res);
}

export async function post<T>(path: string, body?: any): Promise<T> {
  if (isMock())
    return mockFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
  const res = await fetchWithRetry(getUrl(path), {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res);
}

export async function patch<T>(path: string, body: any): Promise<T> {
  if (isMock())
    return mockFetch<T>(path, { method: "PATCH", body: JSON.stringify(body) });
  const res = await fetchWithRetry(getUrl(path), {
    method: "PATCH",
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

export async function put<T>(path: string, body: any): Promise<T> {
  if (isMock())
    return mockFetch<T>(path, { method: "PUT", body: JSON.stringify(body) });
  const res = await fetchWithRetry(getUrl(path), {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return handleResponse<T>(res);
}

export async function del(path: string): Promise<void> {
  if (isMock()) return;
  const res = await fetchWithRetry(getUrl(path), { method: "DELETE" });
  await handleResponse(res);
}

export async function postForm<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  if (isMock()) return mockFetch<T>(path, { method: "POST", body: formData });
  const res = await fetchWithRetry(getUrl(path), {
    method: "POST",
    body: formData,
  });
  return handleResponse<T>(res);
}

// Convenience namespace — pages may import { api } or the named functions
export const api = { get, post, patch, put, del, postForm };
