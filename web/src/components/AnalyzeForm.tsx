import { useId, useState } from "react";
import { ApiError, createBriefing } from "../api";
import type { Briefing, Plan } from "../types";

interface Props {
  readOnly: boolean;
  onCreated: (briefing: Briefing) => void;
}

const PLANS: { value: Plan; label: string }[] = [
  { value: "unknown", label: "Unknown" },
  { value: "free", label: "Free" },
  { value: "pro", label: "Pro" },
  { value: "enterprise", label: "Enterprise" },
];

export function AnalyzeForm({ readOnly, onCreated }: Props) {
  const [inquiry, setInquiry] = useState("");
  const [plan, setPlan] = useState<Plan>("unknown");
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const groupName = useId();
  const logsId = useId();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onCreated(await createBriefing({ inquiry: inquiry.trim(), plan, logs: showLogs ? logs : "" }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  const blank = inquiry.trim() === "";
  return (
    <form className="panel" onSubmit={submit}>
      <section className="panel__section">
        <div className="panel__head">
          <label className="panel__label" htmlFor="inquiry">
            Customer message
          </label>
        </div>
        <textarea
          id="inquiry"
          className="input input--message"
          placeholder="Paste the customer’s email or message, including the subject line if you have it."
          value={inquiry}
          disabled={readOnly}
          onChange={(e) => setInquiry(e.target.value)}
        />
      </section>

      <section className="panel__section panel__section--row">
        <span className="panel__label" id={`${groupName}-label`}>
          Plan
        </span>
        <div className="segments" role="radiogroup" aria-labelledby={`${groupName}-label`}>
          {PLANS.map((p) => (
            <label key={p.value} className="segments__option">
              <input
                type="radio"
                name={groupName}
                value={p.value}
                checked={plan === p.value}
                disabled={readOnly}
                onChange={() => setPlan(p.value)}
              />
              <span>{p.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="panel__section">
        <div className="panel__head">
          <span className="panel__label">
            Logs <span className="panel__optional">optional</span>
          </span>
          <button
            type="button"
            className="chip"
            aria-expanded={showLogs}
            aria-controls={logsId}
            disabled={readOnly}
            onClick={() => setShowLogs((v) => !v)}
          >
            {showLogs ? "Remove logs" : "Add logs"}
          </button>
        </div>
        {showLogs && (
          <textarea
            id={logsId}
            className="input input--logs"
            aria-label="Logs"
            placeholder="Paste JSON or plain-text logs"
            spellCheck={false}
            value={logs}
            disabled={readOnly}
            onChange={(e) => setLogs(e.target.value)}
          />
        )}
      </section>

      {error && (
        <p role="alert" className="error panel__error">
          {error}
        </p>
      )}

      <footer className="panel__footer">
        <p className="panel__hint">
          {readOnly
            ? "Connect the backend to analyze new tickets. Demo data is read-only."
            : "Support Buddy prepares a briefing. It never sends anything."}
        </p>
        <button type="submit" className="button" disabled={readOnly || blank || busy}>
          {busy ? "Preparing…" : "Prepare briefing"}
        </button>
      </footer>
    </form>
  );
}
