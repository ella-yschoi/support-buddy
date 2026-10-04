import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { makeBriefing } from "../test/fixtures";
import { AnalyzeForm } from "./AnalyzeForm";
import { ReplyEditor } from "./ReplyEditor";

vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  approveBriefing: vi.fn(),
  createBriefing: vi.fn(),
}));

const approve = vi.mocked(api.approveBriefing);
const create = vi.mocked(api.createBriefing);

beforeEach(() => {
  vi.resetAllMocks();
});

describe("ReplyEditor", () => {
  it("starts with the draft in an editable box", () => {
    render(<ReplyEditor briefing={makeBriefing()} readOnly={false} onApproved={() => {}} />);
    expect(screen.getByRole("textbox", { name: /reply/i })).toHaveValue(
      "Thanks for reaching out. Please check your storage usage.",
    );
  });

  it("sends the edited text and reports the approved briefing", async () => {
    const approved = makeBriefing({ status: "approved", approved_body: "Edited" });
    approve.mockResolvedValueOnce(approved);
    const onApproved = vi.fn();
    render(<ReplyEditor briefing={makeBriefing()} readOnly={false} onApproved={onApproved} />);

    const box = screen.getByRole("textbox", { name: /reply/i });
    await userEvent.clear(box);
    await userEvent.type(box, "Edited");
    await userEvent.click(screen.getByRole("button", { name: /mark as sent/i }));

    expect(approve).toHaveBeenCalledWith("b-1", "Edited");
    await waitFor(() => expect(onApproved).toHaveBeenCalledWith(approved));
  });

  it("disables sending while the reply is blank", async () => {
    render(<ReplyEditor briefing={makeBriefing()} readOnly={false} onApproved={() => {}} />);
    await userEvent.clear(screen.getByRole("textbox", { name: /reply/i }));
    expect(screen.getByRole("button", { name: /mark as sent/i })).toBeDisabled();
  });

  it("shows a calm error and keeps the text when sending fails", async () => {
    approve.mockRejectedValueOnce(new api.ApiError("This briefing was already sent.", 409));
    render(<ReplyEditor briefing={makeBriefing()} readOnly={false} onApproved={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /mark as sent/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/already sent/i);
    expect(screen.getByRole("textbox", { name: /reply/i })).toHaveValue(
      "Thanks for reaching out. Please check your storage usage.",
    );
  });

  it("copies the current text to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    render(<ReplyEditor briefing={makeBriefing()} readOnly={false} onApproved={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /copy/i }));
    expect(writeText).toHaveBeenCalledWith("Thanks for reaching out. Please check your storage usage.");
    expect(await screen.findByText(/copied/i)).toBeInTheDocument();
  });

  it("is read-only in demo mode but still lets you copy", () => {
    render(<ReplyEditor briefing={makeBriefing()} readOnly onApproved={() => {}} />);
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /mark as sent/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    expect(screen.getByText(/demo data is read-only/i)).toBeInTheDocument();
  });

  it("shows what was sent and how much it changed", () => {
    const sent = makeBriefing({ status: "approved", approved_body: "Final words", edit_ratio: 0.12 });
    render(<ReplyEditor briefing={sent} readOnly={false} onApproved={() => {}} />);
    expect(screen.getByText("Final words")).toBeInTheDocument();
    expect(screen.getByText(/edited 12% from the draft/i)).toBeInTheDocument();
  });

  it("says when it was sent exactly as drafted", () => {
    const sent = makeBriefing({ status: "approved", approved_body: "Same", edit_ratio: 0 });
    render(<ReplyEditor briefing={sent} readOnly={false} onApproved={() => {}} />);
    expect(screen.getByText(/sent as drafted/i)).toBeInTheDocument();
  });

  it("offers an empty reply box for human-only briefings", async () => {
    const human = makeBriefing({ autonomy: "human_only", draft_body: null });
    render(<ReplyEditor briefing={human} readOnly={false} onApproved={() => {}} />);
    const box = screen.getByRole("textbox", { name: /reply/i });
    expect(box).toHaveValue("");
    expect(screen.getByRole("button", { name: /mark as sent/i })).toBeDisabled();
  });
});

describe("AnalyzeForm", () => {
  it("disables submit until a message is entered", async () => {
    render(<AnalyzeForm readOnly={false} onCreated={() => {}} />);
    const submit = screen.getByRole("button", { name: /prepare briefing/i });
    expect(submit).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox", { name: /customer message/i }), "Help me");
    expect(submit).toBeEnabled();
  });

  it("offers the plans as a radio group with Unknown selected by default", () => {
    render(<AnalyzeForm readOnly={false} onCreated={() => {}} />);
    const group = screen.getByRole("radiogroup", { name: /plan/i });
    expect(group).toBeInTheDocument();
    expect(screen.getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual([
      "unknown",
      "free",
      "pro",
      "enterprise",
    ]);
    expect(screen.getByRole("radio", { name: /unknown/i })).toBeChecked();
  });

  it("keeps the logs box hidden until asked, and toggles from the same button spot", async () => {
    render(<AnalyzeForm readOnly={false} onCreated={() => {}} />);
    expect(screen.queryByRole("textbox", { name: /^logs$/i })).not.toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: /add logs/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(screen.getByRole("textbox", { name: /^logs$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remove logs/i })).toHaveAttribute("aria-expanded", "true");
  });

  it("does not send logs that were removed again", async () => {
    create.mockResolvedValueOnce(makeBriefing());
    render(<AnalyzeForm readOnly={false} onCreated={() => {}} />);
    await userEvent.type(screen.getByRole("textbox", { name: /customer message/i }), "Hi");
    await userEvent.click(screen.getByRole("button", { name: /add logs/i }));
    await userEvent.type(screen.getByRole("textbox", { name: /^logs$/i }), "stale");
    await userEvent.click(screen.getByRole("button", { name: /remove logs/i }));
    await userEvent.click(screen.getByRole("button", { name: /prepare briefing/i }));
    expect(create).toHaveBeenCalledWith({ inquiry: "Hi", plan: "unknown", logs: "" });
  });

  it("creates a briefing with the chosen plan and logs", async () => {
    const created = makeBriefing({ id: "fresh" });
    create.mockResolvedValueOnce(created);
    const onCreated = vi.fn();
    render(<AnalyzeForm readOnly={false} onCreated={onCreated} />);

    await userEvent.type(screen.getByRole("textbox", { name: /customer message/i }), "Sync is broken");
    await userEvent.click(screen.getByRole("radio", { name: /enterprise/i }));
    await userEvent.click(screen.getByRole("button", { name: /add logs/i }));
    await userEvent.type(screen.getByRole("textbox", { name: /^logs$/i }), "ERROR boom");
    await userEvent.click(screen.getByRole("button", { name: /prepare briefing/i }));

    expect(create).toHaveBeenCalledWith({ inquiry: "Sync is broken", plan: "enterprise", logs: "ERROR boom" });
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
  });

  it("shows an error and keeps the input when it fails", async () => {
    create.mockRejectedValueOnce(new api.ApiError("We couldn’t reach the server.", 0));
    render(<AnalyzeForm readOnly={false} onCreated={() => {}} />);
    await userEvent.type(screen.getByRole("textbox", { name: /customer message/i }), "Keep me");
    await userEvent.click(screen.getByRole("button", { name: /prepare briefing/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn.t reach/i);
    expect(screen.getByRole("textbox", { name: /customer message/i })).toHaveValue("Keep me");
  });

  it("explains that demo mode cannot analyze new tickets", () => {
    render(<AnalyzeForm readOnly onCreated={() => {}} />);
    expect(screen.getByText(/connect the backend/i)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /customer message/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /prepare briefing/i })).toBeDisabled();
    screen.getAllByRole("radio").forEach((r) => expect(r).toBeDisabled());
  });
});
