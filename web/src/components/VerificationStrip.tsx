import { useId, useState } from "react";
import { humanizeCheck } from "../format";
import type { Check } from "../types";

interface Props {
  checks: Check[];
  score: number;
}

export function VerificationStrip({ checks, score }: Props) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  return (
    <div className="verification">
      <div className="verification__bar">
        <span className="dots" aria-hidden="true">
          {checks.map((c) => (
            <span
              key={c.name}
              data-testid="check-dot"
              data-state={c.passed ? "pass" : "fail"}
              className="dot"
            />
          ))}
        </span>
        <span className="verification__score">{Math.round(score * 100)}%</span>
        <button
          type="button"
          className="link"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Hide details" : "Details"}
        </button>
      </div>
      {open && (
        <ul id={panelId} className="check-list">
          {checks.map((c) => (
            <li key={c.name} data-state={c.passed ? "pass" : "fail"}>
              <span className="check-list__name">{humanizeCheck(c.name)}</span>
              <span className="check-list__detail">{c.detail}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
