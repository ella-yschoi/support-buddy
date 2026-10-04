import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { makeBriefing } from "./test/fixtures";

const briefings = [
  makeBriefing({ id: "one", inquiry_text: "First briefing" }),
  makeBriefing({ id: "two", inquiry_text: "Second briefing", autonomy: "human_only", draft_body: null }),
];

function mockApi(ok: boolean, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok, json: async () => body } as Response),
  );
}

beforeEach(() => {
  window.location.hash = "";
});
afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("shows the queue from the live API without a demo badge", async () => {
    mockApi(true, briefings);
    render(<App />);
    expect(await screen.findByText("First briefing")).toBeInTheDocument();
    expect(screen.queryByText(/demo data/i)).not.toBeInTheDocument();
  });

  it("labels pre-computed data as a demo", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("no api"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ generated_on: "2026-10-04", pipeline: "local", briefings }),
      } as Response);
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    expect(await screen.findByText("First briefing")).toBeInTheDocument();
    expect(screen.getByText(/demo data/i)).toBeInTheDocument();
  });

  it("opens a briefing and returns to the queue", async () => {
    mockApi(true, briefings);
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /open briefing: second briefing/i }));
    expect(await screen.findByText(/no customer-facing draft/i)).toBeInTheDocument();
    expect(window.location.hash).toBe("#/b/two");

    await userEvent.click(screen.getByRole("button", { name: /queue/i }));
    expect(await screen.findByText("First briefing")).toBeInTheDocument();
    expect(window.location.hash).toBe("");
  });

  it("opens the briefing named in the URL", async () => {
    window.location.hash = "#/b/one";
    mockApi(true, briefings);
    render(<App />);
    // The title and the customer-message card both show the inquiry text.
    expect((await screen.findAllByText(/first briefing/i)).length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: /customer message/i })).toBeInTheDocument();
  });

  it("says so when the URL names an unknown briefing", async () => {
    window.location.hash = "#/b/missing";
    mockApi(true, briefings);
    render(<App />);
    expect(await screen.findByText(/couldn.t find that briefing/i)).toBeInTheDocument();
  });

  it("shows a clear error when nothing can be loaded", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    render(<App />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/couldn.t load/i));
  });
});
