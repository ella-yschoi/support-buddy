import { useCallback, useEffect, useState } from "react";
import { loadArchive, loadBriefings } from "./api";
import { AnalyzeForm } from "./components/AnalyzeForm";
import { ArchiveList } from "./components/ArchiveList";
import { BriefingDetail } from "./components/BriefingDetail";
import { Logo } from "./components/Logo";
import { QueueList } from "./components/QueueList";
import { sortQueue } from "./format";
import type { Briefing, Source } from "./types";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; briefings: Briefing[]; source: Source };

type ArchiveState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; briefings: Briefing[] }
  | { status: "error" };

type QueueTab = "pending" | "sent";

type Route = { name: "queue" } | { name: "analyze" } | { name: "briefing"; id: string };

function readRoute(): Route {
  const hash = window.location.hash;
  const briefing = /^#\/b\/(.+)$/.exec(hash);
  if (briefing) return { name: "briefing", id: decodeURIComponent(briefing[1]) };
  if (hash === "#/analyze") return { name: "analyze" };
  return { name: "queue" };
}

function Skeleton() {
  return (
    <div role="status" aria-busy="true" aria-label="Loading the queue" className="skeleton">
      <div className="skeleton__title" />
      <div className="skeleton__line" />
      <div className="group">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="skeleton__row" />
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [route, setRoute] = useState<Route>(readRoute);
  const [queueTab, setQueueTab] = useState<QueueTab>("pending");
  const [archiveState, setArchiveState] = useState<ArchiveState>({ status: "idle" });

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
    const onHashChange = () => setRoute(readRoute());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // Trigger: switch to Sent tab → start loading (if idle)
  useEffect(() => {
    if (queueTab === "sent") {
      setArchiveState((prev) => (prev.status === "idle" ? { status: "loading" } : prev));
    }
  }, [queueTab]);

  // Load: once status is "loading", fetch archive data
  useEffect(() => {
    if (archiveState.status !== "loading") return;
    let cancelled = false;
    loadArchive()
      .then((briefings) => { if (!cancelled) setArchiveState({ status: "ready", briefings }); })
      .catch(() => { if (!cancelled) setArchiveState({ status: "error" }); });
    return () => { cancelled = true; };
  }, [archiveState.status]);

  const go = useCallback((hash: string) => {
    window.location.hash = hash;
    setRoute(readRoute());
  }, []);

  const replace = useCallback((updated: Briefing) => {
    setState((s) =>
      s.status === "ready"
        ? { ...s, briefings: s.briefings.map((b) => (b.id === updated.id ? updated : b)) }
        : s,
    );
  }, []);

  const created = useCallback(
    (briefing: Briefing) => {
      setState((s) =>
        s.status === "ready" ? { ...s, briefings: sortQueue([...s.briefings, briefing]) } : s,
      );
      go(`#/b/${encodeURIComponent(briefing.id)}`);
    },
    [go],
  );

  const archivedDeleted = useCallback((id: string) => {
    setArchiveState((s) =>
      s.status === "ready" ? { ...s, briefings: s.briefings.filter((b) => b.id !== id) } : s,
    );
  }, []);

  const ready = state.status === "ready" ? state : null;
  const readOnly = ready?.source !== "api";
  const queue = ready ? ready.briefings.filter((b) => b.status === "ready") : [];
  const archiveBriefings = archiveState.status === "ready" ? archiveState.briefings : [];
  const selected =
    ready && route.name === "briefing"
      ? (ready.briefings.find((b) => b.id === route.id) ?? archiveBriefings.find((b) => b.id === route.id))
      : undefined;

  return (
    <>
      <header className="topbar">
        <span className="wordmark">
          <Logo />
          Support Buddy
        </span>
        <nav className="nav" aria-label="Main">
          <a href="#/" aria-current={route.name !== "analyze" ? "page" : undefined}>
            Queue
          </a>
          <a href="#/analyze" aria-current={route.name === "analyze" ? "page" : undefined}>
            Analyze
          </a>
        </nav>
        {ready?.source === "demo" && (
          <span
            className="badge"
            title="Pre-computed briefings from the sample golden set. No AI calls are made."
          >
            Demo data
          </span>
        )}
      </header>

      <main className="page">
        {state.status === "loading" && <Skeleton />}

        {state.status === "error" && (
          <p role="alert" className="notice">
            We couldn't load the queue. Check your connection and try again.
          </p>
        )}

        {ready && route.name === "analyze" && (
          <>
            <h1 className="large-title">Analyze</h1>
            <p className="subtitle">Paste a ticket and get a briefing in seconds.</p>
            <AnalyzeForm readOnly={readOnly} onCreated={created} />
          </>
        )}

        {ready && route.name === "briefing" && selected && (
          <BriefingDetail
            briefing={selected}
            onBack={() => go("")}
            readOnly={readOnly}
            onApproved={replace}
          />
        )}

        {ready && route.name === "briefing" && !selected && (
          <div className="notice">
            <p className="notice__title">We couldn't find that briefing.</p>
            <button type="button" className="link" onClick={() => go("")}>
              Back to the queue
            </button>
          </div>
        )}

        {ready && route.name === "queue" && (
          <>
            <h1 className="large-title">Queue</h1>
            <div className="segmented" role="tablist" aria-label="Queue view">
              <button
                type="button"
                role="tab"
                aria-selected={queueTab === "pending"}
                className="segmented__item"
                onClick={() => setQueueTab("pending")}
              >
                Pending <span className="segmented__count">{queue.length}</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={queueTab === "sent"}
                className="segmented__item"
                onClick={() => setQueueTab("sent")}
              >
                Sent
              </button>
            </div>

            {queueTab === "pending" && (
              <QueueList briefings={queue} onOpen={(id) => go(`#/b/${encodeURIComponent(id)}`)} />
            )}

            {queueTab === "sent" && (
              <>
                {archiveState.status === "loading" && <Skeleton />}
                {archiveState.status === "error" && (
                  <p role="alert" className="notice">
                    Couldn't load sent briefings. Check your connection and try again.
                  </p>
                )}
                {archiveState.status === "ready" && (
                  <ArchiveList
                    briefings={archiveBriefings}
                    onOpen={(id) => go(`#/b/${encodeURIComponent(id)}`)}
                    onDeleted={archivedDeleted}
                  />
                )}
              </>
            )}
          </>
        )}
      </main>
    </>
  );
}
