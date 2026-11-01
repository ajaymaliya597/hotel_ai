export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function errorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function extractDetail(payload: unknown): string | null {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) return null;
  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown };
    if (typeof first?.msg === "string") return first.msg;
  }
  return null;
}

const DEFAULT_TIMEOUT_MS = 20_000;

export async function apiFetch<T>(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const external = init.signal;
  const forwardAbort = () => controller.abort();
  external?.addEventListener("abort", forwardAbort);
  const timer = window.setTimeout(forwardAbort, timeoutMs);

  let response: Response;
  try {
    response = await fetch(path, { ...init, signal: controller.signal });
  } catch (error) {
    if (external?.aborted) throw error;
    if (controller.signal.aborted) throw new ApiError("The request took too long. Please try again.", 408);
    throw new ApiError("Could not reach Nova. Check your connection and try again.", 0);
  } finally {
    window.clearTimeout(timer);
    external?.removeEventListener("abort", forwardAbort);
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(extractDetail(payload) ?? `Request failed (${response.status}).`, response.status);
  }
  return payload as T;
}

export async function apiBlob(path: string, body: FormData, signal?: AbortSignal, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Blob> {
  const controller = new AbortController();
  const forwardAbort = () => controller.abort();
  signal?.addEventListener("abort", forwardAbort);
  const timer = window.setTimeout(forwardAbort, timeoutMs);
  try {
    const response = await fetch(path, { method: "POST", body, signal: controller.signal });
    if (!response.ok) {
      const payload: unknown = await response.json().catch(() => null);
      throw new ApiError(extractDetail(payload) ?? `Speech failed (${response.status}).`, response.status);
    }
    return await response.blob();
  } catch (error) {
    if (signal?.aborted || error instanceof ApiError) throw error;
    if (controller.signal.aborted) throw new ApiError("Speech took too long to generate.", 408);
    throw new ApiError("Could not reach Nova for speech playback.", 0);
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", forwardAbort);
  }
}
