import { useState } from "react";
import { ApiError, approveBriefing } from "../api";
import type { Briefing } from "../types";

interface Props {
  briefing: Briefing;
  readOnly: boolean;
  onApproved: (briefing: Briefing) => void;
}

function editNote(ratio: number | null): string | null {
  if (ratio === null) return null;
  return ratio === 0 ? "Sent as drafted" : `Edited ${Math.round(ratio * 100)}% from the draft`;
}

export function ReplyEditor({ briefing, readOnly, onApproved }: Props) {
  const [text, setText] = useState(briefing.draft_body ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copying isn’t available in this browser. Select the text and copy it instead.");
    }
  }

  async function send() {
    setBusy(true);
    setError(null);
    try {
      onApproved(await approveBriefing(briefing.id, text.trim()));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (briefing.status === "approved") {
    const note = editNote(briefing.edit_ratio);
    return (
      <div className="sent">
        <p className="draft">{briefing.approved_body}</p>
        {note && <p className="muted small">{note}</p>}
      </div>
    );
  }

  if (readOnly) {
    return (
      <div>
        {briefing.draft_body !== null && (
          <>
            <p className="draft">{briefing.draft_body}</p>
            <div className="actions">
              <button type="button" className="button button--quiet" onClick={() => copy(briefing.draft_body ?? "")}>
                Copy
              </button>
              <span className="muted small" role="status">
                {copied ? "Copied" : ""}
              </span>
            </div>
          </>
        )}
        <p className="muted small">Demo data is read-only.</p>
      </div>
    );
  }

  const blank = text.trim() === "";
  return (
    <div>
      <textarea
        className="field field--tall"
        aria-label="Your reply"
        placeholder="Write your reply…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="actions">
        <button type="button" className="button button--quiet" disabled={blank} onClick={() => copy(text)}>
          Copy
        </button>
        <button type="button" className="button" disabled={blank || busy} onClick={send}>
          {busy ? "Saving…" : "Mark as sent"}
        </button>
        <span className="muted small" role="status">
          {copied ? "Copied" : ""}
        </span>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <p className="muted small">Support Buddy never sends anything. Send your reply from your own tool, then mark it here.</p>
    </div>
  );
}
