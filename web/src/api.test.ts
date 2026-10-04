import { afterEach, describe, expect, it, vi } from "vitest";
import { loadBriefings } from "./api";
import { makeBriefing } from "./test/fixtures";

const live = [makeBriefing({ id: "live-1" })];
const demo = { generated_on: "2026-10-04", pipeline: "local", briefings: [makeBriefing({ id: "demo-1" })] };

function ok(body: unknown) {
  return { ok: true, json: async () => body } as Response;
}

afterEach(() => vi.unstubAllGlobals());

describe("loadBriefings", () => {
  it("uses the live API when it answers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(ok(live)));
    const result = await loadBriefings();
    expect(result.source).toBe("api");
    expect(result.briefings[0].id).toBe("live-1");
  });

  it("falls back to pre-computed demo data when the API is unreachable", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("network"))
      .mockResolvedValueOnce(ok(demo));
    vi.stubGlobal("fetch", fetchMock);
    const result = await loadBriefings();
    expect(result.source).toBe("demo");
    expect(result.briefings[0].id).toBe("demo-1");
    expect(fetchMock.mock.calls[1][0]).toContain("demo/briefings.json");
  });

  it("falls back when the API route returns a non-JSON page (static hosting)", async () => {
    const html = {
      ok: true,
      json: async () => {
        throw new SyntaxError("Unexpected token <");
      },
    } as unknown as Response;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(html).mockResolvedValueOnce(ok(demo)));
    expect((await loadBriefings()).source).toBe("demo");
  });

  it("falls back when the API answers with an error status", async () => {
    const bad = { ok: false, status: 500, json: async () => ({}) } as Response;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(bad).mockResolvedValueOnce(ok(demo)));
    expect((await loadBriefings()).source).toBe("demo");
  });

  it("throws when neither source is available", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    await expect(loadBriefings()).rejects.toThrow();
  });
});
