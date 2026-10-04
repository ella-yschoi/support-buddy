import { describe, expect, it } from "vitest";
import { categoryLabel, displayTitle, formatTime, needsAttention, verdict } from "./format";
import { makeBriefing } from "./test/fixtures";

describe("verdict", () => {
  it("is ready when sufficient and not human-only", () => {
    expect(verdict(makeBriefing())).toBe("Briefing ready");
    expect(needsAttention(makeBriefing())).toBe(false);
  });

  it("needs your eyes when the briefing is insufficient", () => {
    const b = makeBriefing({ sufficiency: "insufficient" });
    expect(verdict(b)).toBe("Needs your eyes");
    expect(needsAttention(b)).toBe(true);
  });

  it("needs your eyes for human-only even when sufficient", () => {
    expect(verdict(makeBriefing({ autonomy: "human_only" }))).toBe("Needs your eyes");
  });
});

describe("formatTime", () => {
  it("formats morning, noon, afternoon and midnight in 12-hour time", () => {
    expect(formatTime("2026-10-04T02:05:00")).toBe("2:05 AM");
    expect(formatTime("2026-10-04T12:00:00")).toBe("12:00 PM");
    expect(formatTime("2026-10-04T15:30:00")).toBe("3:30 PM");
    expect(formatTime("2026-10-04T00:09:00")).toBe("12:09 AM");
  });

  it("returns the input unchanged when it is not a timestamp", () => {
    expect(formatTime("yesterday")).toBe("yesterday");
  });
});

describe("displayTitle", () => {
  it("uses the email subject when the inquiry starts with one", () => {
    expect(displayTitle("Subject: Urgent - Files not syncing\n\nHi team, nothing works.")).toBe(
      "Urgent - Files not syncing",
    );
  });

  it("uses the first sentence otherwise, without the trailing period", () => {
    expect(displayTitle("Files stopped syncing and I see SYNC-002. Please help.")).toBe(
      "Files stopped syncing and I see SYNC-002",
    );
  });

  it("keeps a question mark", () => {
    expect(displayTitle("How do I enable two-factor authentication? Thanks")).toBe(
      "How do I enable two-factor authentication?",
    );
  });

  it("cuts long titles at a word boundary with an ellipsis", () => {
    const title = displayTitle(
      "URGENT: Starting 30 minutes ago none of our employees can log into CloudSync through Okta SSO and this is serious",
    );
    expect(title.endsWith("…")).toBe(true);
    expect(title.length).toBeLessThanOrEqual(73);
    expect(title).not.toMatch(/\s…$/);
    expect(title).toBe("URGENT: Starting 30 minutes ago none of our employees can log into…");
  });

  it("collapses whitespace and handles empty input", () => {
    expect(displayTitle("  Files \n  are   gone  ")).toBe("Files are gone");
    expect(displayTitle("   ")).toBe("Untitled inquiry");
  });
});

describe("categoryLabel", () => {
  it("capitalizes plain categories, upper-cases API and renames unknown", () => {
    expect(categoryLabel("sync")).toBe("Sync");
    expect(categoryLabel("api")).toBe("API");
    expect(categoryLabel("unknown")).toBe("Unclassified");
  });
});
