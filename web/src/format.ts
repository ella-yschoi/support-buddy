import type { Autonomy, Briefing, Severity } from "./types";

export function needsAttention(b: Briefing): boolean {
  return b.autonomy === "human_only" || b.sufficiency === "insufficient";
}

export function verdict(b: Briefing): string {
  return needsAttention(b) ? "Needs your eyes" : "Briefing ready";
}

export const AUTONOMY_LABEL: Record<Autonomy, string> = {
  auto: "Auto",
  confirm: "Confirm",
  human_only: "Human-only",
};

export const SEVERITY_LABEL: Record<Severity, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export function formatTime(iso: string): string {
  const match = /T(\d{2}):(\d{2})/.exec(iso);
  if (!match) return iso;
  const hour24 = Number(match[1]);
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12;
  return `${hour12}:${match[2]} ${hour24 < 12 ? "AM" : "PM"}`;
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function humanizeCheck(name: string): string {
  return capitalize(name.replace(/_/g, " "));
}

const CATEGORY_LABEL: Record<string, string> = { api: "API", unknown: "Unclassified" };

export function categoryLabel(category: string): string {
  return CATEGORY_LABEL[category] ?? capitalize(category);
}

const MAX_TITLE = 70;

/** A short, readable title taken from what the customer actually wrote. */
export function displayTitle(inquiry: string): string {
  const subject = /^\s*Subject:\s*(.+)$/im.exec(inquiry);
  let text = (subject ? subject[1] : inquiry).replace(/\s+/g, " ").trim();
  if (!text) return "Untitled inquiry";

  const sentence = /^(.{15,}?[.?!])(?:\s|$)/.exec(text);
  if (sentence) text = sentence[1];
  text = text.replace(/[.,;:]+$/, "");

  if (text.length > MAX_TITLE) {
    const cut = text.slice(0, MAX_TITLE + 1);
    const lastSpace = cut.lastIndexOf(" ");
    text = `${cut.slice(0, lastSpace > 20 ? lastSpace : MAX_TITLE).trimEnd()}…`;
  }
  return text;
}

const SEVERITY_RANK: Record<Severity, number> = { low: 0, medium: 1, high: 2, critical: 3 };

/** Most severe first, oldest first within a severity (the order the server uses). */
export function sortQueue(briefings: Briefing[]): Briefing[] {
  return [...briefings].sort(
    (a, b) =>
      SEVERITY_RANK[b.effective_severity] - SEVERITY_RANK[a.effective_severity] ||
      a.created_at.localeCompare(b.created_at),
  );
}
