import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { clearAccessKey, getAccessKey } from "./api";
import { makeBriefing } from "./test/fixtures";

const live = [makeBriefing({ id: "live-1", inquiry_text: "Live ticket from the server" })];
const demo = {
  generated_on: "x",
  pipeline: "local",
  briefings: [makeBriefing({ id: "demo-1", inquiry_text: "Demo ticket" })],
};

/** A server that only answers /api/ requests carrying `Bearer good`. */
function lockedServer() {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const headers = (init?.headers ?? {}) as Record<string, string>;
    if (String(url).includes("/demo/briefings.json")) {
      return Promise.resolve({ ok: true, status: 200, json: async () => demo } as Response);
    }
    const authorised = headers.Authorization === "Bearer good";
    return Promise.resolve({
      ok: authorised,
      status: authorised ? 200 : 401,
      json: async () => (authorised ? live : { detail: "Unauthorized" }),
    } as Response);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  clearAccessKey();
  window.location.hash = "";
});
afterEach(() => {
  clearAccessKey();
  vi.unstubAllGlobals();
});

describe("unlocking live data", () => {
  it("shows demo data and an Unlock button when the server asks for a key", async () => {
    lockedServer();
    render(<App />);
    expect(await screen.findByText("Demo ticket")).toBeInTheDocument();
    expect(screen.getByText(/demo data/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^unlock$/i })).toBeInTheDocument();
  });

  it("switches to live data when the right key is entered", async () => {
    lockedServer();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /^unlock$/i }));
    await userEvent.type(screen.getByLabelText(/access key/i), "good");
    await userEvent.click(screen.getByRole("button", { name: /^unlock live data$/i }));

    expect(await screen.findByText("Live ticket from the server")).toBeInTheDocument();
    expect(screen.queryByText(/demo data/i)).not.toBeInTheDocument();
    expect(getAccessKey()).toBe("good");
    expect(screen.getByRole("button", { name: /^lock$/i })).toBeInTheDocument();
  });

  it("rejects a wrong key, forgets it, and stays on demo data", async () => {
    lockedServer();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /^unlock$/i }));
    await userEvent.type(screen.getByLabelText(/access key/i), "bad");
    await userEvent.click(screen.getByRole("button", { name: /^unlock live data$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/wasn.t accepted/i);
    expect(getAccessKey()).toBe("");
    expect(screen.getByText("Demo ticket")).toBeInTheDocument();
  });

  it("uses a key remembered for this tab without asking again", async () => {
    sessionStorage.setItem("sb_access_key", "good");
    lockedServer();
    render(<App />);
    expect(await screen.findByText("Live ticket from the server")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^unlock$/i })).not.toBeInTheDocument();
  });

  it("locks again on request: forgets the key and returns to demo data", async () => {
    sessionStorage.setItem("sb_access_key", "good");
    lockedServer();
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: /^lock$/i }));

    expect(await screen.findByText("Demo ticket")).toBeInTheDocument();
    expect(getAccessKey()).toBe("");
    await waitFor(() => expect(screen.getByRole("button", { name: /^unlock$/i })).toBeInTheDocument());
  });

  it("offers no Unlock button when the API is just unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        String(url).includes("/demo/")
          ? Promise.resolve({ ok: true, status: 200, json: async () => demo } as Response)
          : Promise.reject(new TypeError("offline")),
      ),
    );
    render(<App />);
    await screen.findByText("Demo ticket");
    expect(screen.queryByRole("button", { name: /^unlock$/i })).not.toBeInTheDocument();
  });
});
