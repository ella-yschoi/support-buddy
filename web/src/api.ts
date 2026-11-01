import type { Briefing, Plan, Source } from "./types";

const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

// The access key is typed in by the person using the app and kept only for this tab
// (sessionStorage). It must never come from a build-time variable: everything in a Vite
// bundle is readable by every visitor.
const KEY_NAME = "sb_access_key";

export function getAccessKey(): string {
  try {
    return sessionStorage.getItem(KEY_NAME) ?? "";
  } catch {
    return "";
  }
}

export function setAccessKey(key: string): void {
  try {
    sessionStorage.setItem(KEY_NAME, key.trim());
  } catch {
    /* storage blocked: the key just will not be remembered */
  }
}

export function clearAccessKey(): void {
  try {
    sessionStorage.removeItem(KEY_NAME);
  } catch {
    /* nothing to clear */
  }
}

function authHeaders(): Record<string, string> {
  const key = getAccessKey();
  return key ? { Authorization: `Bearer ${key}` } : {};
}

class HttpError extends Error {
  readonly status: number;

  constructor(url: string, status: number) {
    super(`${url} answered ${status}`);
    this.status = status;
  }
}

async function getJson(url: string, withAuth = true): Promise<unknown> {
  const response = await fetch(url, { headers: withAuth ? authHeaders() : {} });
  if (!response.ok) throw new HttpError(url, response.status);
  return response.json();
}

export interface LoadedQueue {
  briefings: Briefing[];
  source: Source;
  /** The API answered 401: it is reachable but wants an access key. */
  locked: boolean;
}

/**
 * The live API when it answers; otherwise the pre-computed demo briefings that ship with the
 * site. Static hosts answer unknown routes with an HTML page, so a body that is not the
 * expected JSON counts as "API unavailable" too.
 */
export async function loadBriefings(): Promise<LoadedQueue> {
  try {
    const data = await getJson(`${API_BASE}/api/v1/briefings`);
    if (!Array.isArray(data)) throw new Error("unexpected API payload");
    return { briefings: data as Briefing[], source: "api", locked: false };
  } catch (error) {
    const locked = error instanceof HttpError && error.status === 401;
    const demo = (await getJson(`${import.meta.env.BASE_URL}demo/briefings.json`, false)) as {
      briefings?: Briefing[];
    };
    if (!Array.isArray(demo.briefings)) throw new Error("demo data is malformed");
    return { briefings: demo.briefings, source: "demo", locked };
  }
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function friendlyMessage(status: number): string {
  switch (status) {
    case 401:
      return "An access key is needed. Unlock and try again.";
    case 404:
      return "We couldn’t find that briefing.";
    case 429:
      return "Too many requests. Wait a minute and try again.";
    case 409:
      return "This briefing was already sent.";
    case 422:
      return "Please check the form and try again.";
    default:
      return `Something went wrong on the server (${status}).`;
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", ...authHeaders() },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError("We couldn’t reach the server.", 0);
  }
  if (!response.ok) throw new ApiError(friendlyMessage(response.status), response.status);
  return (await response.json()) as T;
}

export function createBriefing(req: { inquiry: string; plan: Plan; logs: string }): Promise<Briefing> {
  return post<Briefing>("/api/v1/briefings", req);
}

export function approveBriefing(id: string, finalBody: string): Promise<Briefing> {
  return post<Briefing>(`/api/v1/briefings/${encodeURIComponent(id)}/approve`, {
    final_body: finalBody,
  });
}

export async function loadArchive(): Promise<Briefing[]> {
  const data = await getJson(`${API_BASE}/api/v1/briefings/archive`);
  if (!Array.isArray(data)) throw new Error("unexpected API payload");
  return data as Briefing[];
}

export async function deleteBriefing(id: string): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/briefings/${encodeURIComponent(id)}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
  } catch {
    throw new ApiError("We couldn't reach the server.", 0);
  }
  if (!response.ok) throw new ApiError(friendlyMessage(response.status), response.status);
}
