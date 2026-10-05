import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeBriefing } from "../test/fixtures";
import { AutonomyPill } from "./AutonomyPill";
import { BriefingDetail } from "./BriefingDetail";
import { QueueList } from "./QueueList";
import { VerificationStrip } from "./VerificationStrip";

describe("AutonomyPill", () => {
  it.each([
    ["auto", "Auto"],
    ["confirm", "Confirm"],
    ["human_only", "Human-only"],
  ] as const)("labels %s as %s", (level, label) => {
    render(<AutonomyPill level={level} simulated={false} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("explains that simulated auto never sends", () => {
    render(<AutonomyPill level="auto" simulated />);
    expect(screen.getByLabelText(/would auto-send/i)).toBeInTheDocument();
  });
});

describe("VerificationStrip", () => {
  const checks = [
    { name: "citations_exist", passed: true, detail: "1 sources found" },
    { name: "no_commitments", passed: false, detail: "commitment language: refund" },
    { name: "pii_leak", passed: true, detail: "no leaked values" },
  ];

  it("shows one dot per check and marks the failed one", () => {
    render(<VerificationStrip checks={checks} score={0.8} />);
    const dots = screen.getAllByTestId("check-dot");
    expect(dots).toHaveLength(3);
    expect(dots.map((d) => d.getAttribute("data-state"))).toEqual(["pass", "fail", "pass"]);
  });

  it("shows the score as a percentage", () => {
    render(<VerificationStrip checks={checks} score={0.8} />);
    expect(screen.getByText("80%")).toBeInTheDocument();
  });

  it("keeps details hidden until expanded", async () => {
    render(<VerificationStrip checks={checks} score={0.8} />);
    expect(screen.queryByText(/commitment language: refund/)).not.toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: /details/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/commitment language: refund/)).toBeInTheDocument();
  });
});

describe("QueueList", () => {
  const items = [
    makeBriefing({ id: "a", inquiry_text: "Alpha outage", autonomy: "human_only", effective_severity: "critical" }),
    makeBriefing({ id: "b", inquiry_text: "Beta question", autonomy: "auto", simulated: true }),
    makeBriefing({ id: "c", inquiry_text: "Gamma sync", autonomy: "confirm", sufficiency: "insufficient" }),
  ];

  it("lists briefings in the order given", () => {
    render(<QueueList briefings={items} onOpen={() => {}} />);
    const rows = screen.getAllByRole("button", { name: /open briefing/i });
    expect(rows.map((r) => within(r).getByRole("heading").textContent)).toEqual([
      "Alpha outage",
      "Beta question",
      "Gamma sync",
    ]);
  });

  it("shows counts per autonomy level on the filters", () => {
    render(<QueueList briefings={items} onOpen={() => {}} />);
    expect(screen.getByRole("tab", { name: /all 3/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /auto 1/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /confirm 1/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /human-only 1/i })).toBeInTheDocument();
  });

  it("filters by autonomy level", async () => {
    render(<QueueList briefings={items} onOpen={() => {}} />);
    await userEvent.click(screen.getByRole("tab", { name: /human-only/i }));
    expect(screen.getByText("Alpha outage")).toBeInTheDocument();
    expect(screen.queryByText("Beta question")).not.toBeInTheDocument();
  });

  it("shows the verdict line for each row", () => {
    render(<QueueList briefings={items} onOpen={() => {}} />);
    expect(screen.getAllByText("Needs your eyes")).toHaveLength(2);
    expect(screen.getAllByText("Briefing ready")).toHaveLength(1);
  });

  it("calls onOpen with the briefing id", async () => {
    const onOpen = vi.fn();
    render(<QueueList briefings={items} onOpen={onOpen} />);
    await userEvent.click(screen.getByRole("button", { name: /open briefing: beta question/i }));
    expect(onOpen).toHaveBeenCalledWith("b");
  });

  it("shows a calm empty state", () => {
    render(<QueueList briefings={[]} onOpen={() => {}} />);
    expect(screen.getByText(/nothing waiting/i)).toBeInTheDocument();
  });
});

describe("BriefingDetail", () => {
  it("shows the customer message, routing reasons, hypotheses and draft", () => {
    render(<BriefingDetail briefing={makeBriefing()} onBack={() => {}} />);
    const message = within(screen.getByRole("region", { name: /customer message/i }));
    expect(message.getByText(/files stopped syncing/i)).toBeInTheDocument();
    expect(screen.getByText(/not auto-eligible/i)).toBeInTheDocument();
    expect(screen.getByText("Storage quota exceeded")).toBeInTheDocument();
    expect(screen.getByText(/please check your storage usage/i)).toBeInTheDocument();
  });

  it("never shows a draft for human-only briefings and says why", () => {
    const b = makeBriefing({
      autonomy: "human_only",
      draft_body: null,
      autonomy_reasons: ["Sensitive topic in message: breach"],
    });
    render(<BriefingDetail briefing={b} onBack={() => {}} />);
    expect(screen.getByText(/no customer-facing draft/i)).toBeInTheDocument();
    expect(screen.getByText(/sensitive topic in message: breach/i)).toBeInTheDocument();
  });

  it("lists what is missing when the briefing is insufficient", () => {
    const b = makeBriefing({
      sufficiency: "insufficient",
      sufficiency_reasons: ["No log evidence: ask the customer for logs"],
    });
    render(<BriefingDetail briefing={b} onBack={() => {}} />);
    expect(screen.getByText(/ask the customer for logs/i)).toBeInTheDocument();
    expect(screen.getByText(/start from the raw logs/i)).toBeInTheDocument();
  });

  it("hides evidence until the hypothesis is expanded", async () => {
    render(<BriefingDetail briefing={makeBriefing()} onBack={() => {}} />);
    expect(screen.queryByText(/ERROR SYNC-002 upload failed/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /show evidence/i }));
    expect(screen.getByText(/ERROR SYNC-002 upload failed/)).toBeInTheDocument();
  });

  it("calls onBack", async () => {
    const onBack = vi.fn();
    render(<BriefingDetail briefing={makeBriefing()} onBack={onBack} />);
    await userEvent.click(screen.getByRole("button", { name: /queue/i }));
    expect(onBack).toHaveBeenCalled();
  });
});


describe("ticket origin", () => {
  const origin = {
    source: "linear",
    external_id: "abc",
    key: "SUP-7",
    url: "https://linear.app/x/issue/SUP-7",
  };

  it("shows the ticket key in the queue row when the briefing came from a ticket tool", () => {
    render(<QueueList briefings={[makeBriefing({ origin })]} onOpen={() => {}} />);
    expect(screen.getByText(/SUP-7/)).toBeInTheDocument();
  });

  it("shows no key for pasted tickets", () => {
    render(<QueueList briefings={[makeBriefing()]} onOpen={() => {}} />);
    expect(screen.queryByText(/SUP-/)).not.toBeInTheDocument();
  });

  it("links to the ticket in its own tool, opening safely in a new tab", () => {
    render(<BriefingDetail briefing={makeBriefing({ origin })} onBack={() => {}} />);
    const link = screen.getByRole("link", { name: /open sup-7 in linear/i });
    expect(link).toHaveAttribute("href", origin.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("names each tool properly", () => {
    const zendesk = { ...origin, source: "zendesk", key: "#412" };
    render(<BriefingDetail briefing={makeBriefing({ origin: zendesk })} onBack={() => {}} />);
    expect(screen.getByRole("link", { name: /open #412 in zendesk/i })).toBeInTheDocument();
  });

  it("has no ticket link for pasted tickets", () => {
    render(<BriefingDetail briefing={makeBriefing()} onBack={() => {}} />);
    expect(screen.queryByRole("link", { name: /open .* in /i })).not.toBeInTheDocument();
  });

  it("rejects non-http links rather than rendering them", () => {
    const evil = { ...origin, url: "javascript:alert(1)" };
    render(<BriefingDetail briefing={makeBriefing({ origin: evil })} onBack={() => {}} />);
    expect(screen.queryByRole("link", { name: /open sup-7/i })).not.toBeInTheDocument();
  });
});
