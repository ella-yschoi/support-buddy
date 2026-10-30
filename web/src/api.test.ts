import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  approveBriefing,
  clearAccessKey,
  createBriefing,
  getAccessKey,
  loadBriefings,
  setAccessKey,
} from "./api";
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


describe("access key", () => {
  beforeEach(() => clearAccessKey());
  afterEach(() => {
    clearAccessKey();
    vi.unstubAllGlobals();
  });

  it("is remembered for the tab and can be cleared", () => {
    expect(getAccessKey()).toBe("");
    setAccessKey("  abc123  ");
    expect(getAccessKey()).toBe("abc123");
    clearAccessKey();
    expect(getAccessKey()).toBe("");
  });

  it("is kept in sessionStorage, which dies with the tab, never in localStorage", () => {
    setAccessKey("abc123");
    expect(sessionStorage.getItem("sb_access_key")).toBe("abc123");
    expect(localStorage.length).toBe(0);
  });

  it("does not throw when storage is blocked", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(getAccessKey()).toBe("");
    expect(() => setAccessKey("x")).not.toThrow();
    vi.restoreAllMocks();
  });

  it("is sent as a bearer token when set, and not at all when empty", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(live));
    vi.stubGlobal("fetch", fetchMock);
    await loadBriefings();
    expect(fetchMock.mock.calls[0][1].headers).toEqual({});

    setAccessKey("abc123");
    await loadBriefings();
    expect(fetchMock.mock.calls[1][1].headers).toEqual({ Authorization: "Bearer abc123" });
  });

  it("is never sent to the static demo file", async () => {
    setAccessKey("abc123");
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(ok(demo));
    vi.stubGlobal("fetch", fetchMock);
    await loadBriefings();
    expect(String(fetchMock.mock.calls[1][0])).toContain("demo/briefings.json");
    expect(fetchMock.mock.calls[1][1]?.headers ?? {}).toEqual({});
  });

  it("is not read from a build-time variable that would ship inside the public bundle", async () => {
    const { readFileSync } = await import("node:fs");
    const { resolve } = await import("node:path");
    const source = readFileSync(resolve(__dirname, "api.ts"), "utf8");
    expect(source).not.toContain("VITE_API_SECRET_KEY");
  });
});

describe("locked state", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("tells the app the API is locked when it answers 401, and still shows demo data", async () => {
    const locked = { ok: false, status: 401, json: async () => ({}) } as Response;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(locked).mockResolvedValueOnce(ok(demo)));
    const result = await loadBriefings();
    expect(result).toMatchObject({ source: "demo", locked: true });
  });

  it("is not locked when the API is simply unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValueOnce(new TypeError("offline")).mockResolvedValueOnce(ok(demo)),
    );
    expect(await loadBriefings()).toMatchObject({ source: "demo", locked: false });
  });

  it("is not locked when the live API answers", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(ok(live)));
    expect(await loadBriefings()).toMatchObject({ source: "api", locked: false });
  });

  it("explains 401 and 429 in plain words", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) }));
    await expect(createBriefing({ inquiry: "x", plan: "pro", logs: "" })).rejects.toMatchObject({
      status: 401,
      message: expect.stringMatching(/access key/i),
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: false, status: 429, json: async () => ({}) }));
    await expect(createBriefing({ inquiry: "x", plan: "pro", logs: "" })).rejects.toMatchObject({
      status: 429,
      message: expect.stringMatching(/too many|wait/i),
    });
  });
});
