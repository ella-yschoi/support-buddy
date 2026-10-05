import type { Briefing, Plan, Source } from "./types";

const API_BASE: string = import.meta.env.VITE_API_URL ?? "";

async function getJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} answered ${response.status}`);
  return response.json();
}

export interface LoadedQueue {
  briefings: Briefing[];
  source: Source;
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
    return { briefings: data as Briefing[], source: "api" };
  } catch {
    const demo = (await getJson(`${import.meta.env.BASE_URL}demo/briefings.json`)) as {
      briefings?: Briefing[];
    };
    if (!Array.isArray(demo.briefings)) throw new Error("demo data is malformed");
    return { briefings: demo.briefings, source: "demo" };
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
    case 404:
      return "We couldn’t find that briefing.";
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
      headers: { "content-type": "application/json" },
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
