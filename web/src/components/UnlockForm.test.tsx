import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UnlockForm } from "./UnlockForm";

describe("UnlockForm", () => {
  it("hides what is typed", () => {
    render(<UnlockForm onUnlock={async () => "ok"} onCancel={() => {}} />);
    expect(screen.getByLabelText(/access key/i)).toHaveAttribute("type", "password");
  });

  it("will not submit an empty key", () => {
    render(<UnlockForm onUnlock={async () => "ok"} onCancel={() => {}} />);
    expect(screen.getByRole("button", { name: /^unlock live data$/i })).toBeDisabled();
  });

  it("passes the typed key on submit", async () => {
    const onUnlock = vi.fn().mockResolvedValue("ok");
    render(<UnlockForm onUnlock={onUnlock} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText(/access key/i), "abc123");
    await userEvent.click(screen.getByRole("button", { name: /^unlock live data$/i }));
    expect(onUnlock).toHaveBeenCalledWith("abc123");
  });

  it("says when the key was not accepted and keeps the form open", async () => {
    render(<UnlockForm onUnlock={async () => "rejected"} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText(/access key/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /^unlock live data$/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/wasn.t accepted/i);
  });

  it("says when the server could not be reached, instead of blaming the key", async () => {
    render(<UnlockForm onUnlock={async () => "offline"} onCancel={() => {}} />);
    await userEvent.type(screen.getByLabelText(/access key/i), "abc");
    await userEvent.click(screen.getByRole("button", { name: /^unlock live data$/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn.t reach/i);
  });

  it("can be cancelled", async () => {
    const onCancel = vi.fn();
    render(<UnlockForm onUnlock={async () => "ok"} onCancel={onCancel} />);
    await userEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });
});
