import type { Briefing, Source } from "./types";

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
