import { useCallback, useEffect, useState } from "react";
import { loadBriefings } from "./api";
import { BriefingDetail } from "./components/BriefingDetail";
import { QueueList } from "./components/QueueList";
import type { Briefing, Source } from "./types";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; briefings: Briefing[]; source: Source };

function readRoute(): string | null {
  const match = /^#\/b\/(.+)$/.exec(window.location.hash);
  return match ? decodeURIComponent(match[1]) : null;
}

export default function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [openId, setOpenId] = useState<string | null>(readRoute);

  useEffect(() => {
    let cancelled = false;
    loadBriefings()
      .then(({ briefings, source }) => !cancelled && setState({ status: "ready", briefings, source }))
      .catch(() => !cancelled && setState({ status: "error" }));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const onHashChange = () => setOpenId(readRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const open = useCallback((id: string) => {
    window.location.hash = `#/b/${encodeURIComponent(id)}`;
    setOpenId(id);
  }, []);
  const back = useCallback(() => {
    window.location.hash = "";
    setOpenId(null);
  }, []);

  const selected =
    state.status === "ready" && openId ? state.briefings.find((b) => b.id === openId) : undefined;

  return (
    <>
      <header className="topbar">
        <span className="wordmark">Support Buddy</span>
        {state.status === "ready" && state.source === "demo" && (
          <span
            className="badge"
            title="Pre-computed briefings from the sample golden set. No AI calls are made."
          >
            Demo data
          </span>
        )}
      </header>

      <main className="page">
        {state.status === "loading" && <p className="muted" aria-live="polite">Loading…</p>}

        {state.status === "error" && (
          <p role="alert" className="notice">
            We couldn’t load the queue. Check your connection and try again.
          </p>
        )}

        {state.status === "ready" && openId && selected && (
          <BriefingDetail briefing={selected} onBack={back} />
        )}

        {state.status === "ready" && openId && !selected && (
          <div className="notice">
            <p className="notice__title">We couldn’t find that briefing.</p>
            <button type="button" className="link" onClick={back}>
              Back to the queue
            </button>
          </div>
        )}

        {state.status === "ready" && !openId && (
          <>
            <h1 className="large-title">Queue</h1>
            <p className="subtitle">
              {state.briefings.length === 0
                ? "All caught up."
                : `${state.briefings.length} briefings prepared before you logged in.`}
            </p>
            <QueueList briefings={state.briefings} onOpen={open} />
          </>
        )}
      </main>
    </>
  );
}
