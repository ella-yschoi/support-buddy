import { useId, useState } from "react";

export type UnlockResult = "ok" | "rejected" | "offline";

interface Props {
  onUnlock: (key: string) => Promise<UnlockResult>;
  onCancel: () => void;
}

const MESSAGE: Record<Exclude<UnlockResult, "ok">, string> = {
  rejected: "That key wasn’t accepted.",
  offline: "We couldn’t reach the server. Try again in a moment.",
};

export function UnlockForm({ onUnlock, onCancel }: Props) {
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Exclude<UnlockResult, "ok"> | null>(null);
  const inputId = useId();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setProblem(null);
    try {
      const result = await onUnlock(key.trim());
      if (result !== "ok") setProblem(result);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="unlock" onSubmit={submit} aria-label="Unlock live data">
      <label className="label" htmlFor={inputId}>
        Access key
      </label>
      <input
        id={inputId}
        className="input"
        type="password"
        autoComplete="off"
        spellCheck={false}
        value={key}
        onChange={(e) => setKey(e.target.value)}
      />
      {problem && (
        <p role="alert" className="error">
          {MESSAGE[problem]}
        </p>
      )}
      <div className="actions">
        <button type="submit" className="button" disabled={key.trim() === "" || busy}>
          {busy ? "Checking…" : "Unlock live data"}
        </button>
        <button type="button" className="link" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
