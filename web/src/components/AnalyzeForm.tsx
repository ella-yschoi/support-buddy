import { useState } from "react";
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
    <form className="card form" onSubmit={submit}>
      <label className="label" htmlFor="inquiry">
        Customer message
      </label>
      <textarea
        id="inquiry"
        className="field field--tall"
        placeholder="Paste the customer’s email or message"
        value={inquiry}
        disabled={readOnly}
        onChange={(e) => setInquiry(e.target.value)}
      />

      <div className="form__row">
        <label className="label" htmlFor="plan">
          Plan
        </label>
        <select
          id="plan"
          className="field field--select"
          value={plan}
          disabled={readOnly}
          onChange={(e) => setPlan(e.target.value as Plan)}
        >
          {PLANS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
        <button type="button" className="link" disabled={readOnly} onClick={() => setShowLogs((v) => !v)}>
          {showLogs ? "Remove logs" : "Add logs"}
        </button>
      </div>

      {showLogs && (
        <>
          <label className="label" htmlFor="logs">
            Logs
          </label>
          <textarea
            id="logs"
            className="field field--mono"
            placeholder="Paste JSON or plain-text logs"
            value={logs}
            disabled={readOnly}
            onChange={(e) => setLogs(e.target.value)}
          />
        </>
      )}

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {readOnly && (
        <p className="muted small">Connect the backend to analyze new tickets. Demo data is read-only.</p>
      )}

      <div className="actions">
        <button type="submit" className="button" disabled={readOnly || blank || busy}>
          {busy ? "Preparing…" : "Prepare briefing"}
        </button>
      </div>
    </form>
  );
}
