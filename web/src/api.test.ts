import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, approveBriefing, createBriefing, loadBriefings } from "./api";
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

describe("createBriefing", () => {
  it("posts the inquiry, plan and logs and returns the briefing", async () => {
    const created = makeBriefing({ id: "new-1" });
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, status: 201, json: async () => created });
    vi.stubGlobal("fetch", fetchMock);

    const result = await createBriefing({ inquiry: "Help", plan: "pro", logs: "" });

    expect(result.id).toBe("new-1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/briefings");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ inquiry: "Help", plan: "pro", logs: "" });
  });

  it("turns a validation error into a friendly ApiError", async () => {
    const bad = { ok: false, status: 422, json: async () => ({ detail: [{ msg: "must not be blank" }] }) };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(bad));
    await expect(createBriefing({ inquiry: " ", plan: "pro", logs: "" })).rejects.toMatchObject({
      status: 422,
      message: expect.stringMatching(/check/i),
    });
  });

  it("reports an unreachable server with status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError("offline")));
    const error = await createBriefing({ inquiry: "x", plan: "pro", logs: "" }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
  });
});

describe("approveBriefing", () => {
  it("posts the final text to the approve endpoint", async () => {
    const approved = makeBriefing({ id: "b-9", status: "approved", approved_body: "Sent text" });
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, status: 200, json: async () => approved });
    vi.stubGlobal("fetch", fetchMock);

    const result = await approveBriefing("b-9", "Sent text");

    expect(result.status).toBe("approved");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/briefings/b-9/approve");
    expect(JSON.parse(init.body)).toEqual({ final_body: "Sent text" });
  });

  it("explains a conflict when it was already sent", async () => {
    const conflict = { ok: false, status: 409, json: async () => ({ detail: "already approved" }) };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(conflict));
    await expect(approveBriefing("b-9", "x")).rejects.toMatchObject({
      status: 409,
      message: expect.stringMatching(/already/i),
    });
  });
});
