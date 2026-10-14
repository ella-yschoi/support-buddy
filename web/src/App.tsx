import { useCallback, useEffect, useState } from "react";
import { loadArchive, loadBriefings } from "./api";
import { AnalyzeForm } from "./components/AnalyzeForm";
import { ArchiveList } from "./components/ArchiveList";
import { BriefingDetail } from "./components/BriefingDetail";
import { Logo } from "./components/Logo";
import { QueueList } from "./components/QueueList";
import { sortQueue } from "./format";
import { AUTONOMY_LABEL } from "./format";
import type { Autonomy, Briefing, Source } from "./types";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; briefings: Briefing[]; source: Source };

type ArchiveState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; briefings: Briefing[] }
  | { status: "error" };

type Filter = "all" | Autonomy | "sent";
const FILTERS: Filter[] = ["all", "auto", "confirm", "human_only", "sent"];

type Route = { name: "queue" } | { name: "analyze" } | { name: "briefing"; id: string };

function readRoute(): Route {
  const hash = window.location.hash;
  const briefing = /^#\/b\/(.+)$/.exec(hash);
  if (briefing) return { name: "briefing", id: decodeURIComponent(briefing[1]) };
  if (hash === "#/analyze") return { name: "analyze" };
  return { name: "queue" };
}

function filterLabel(f: Filter): string {
  if (f === "all") return "All";
  if (f === "sent") return "Sent";
  return AUTONOMY_LABEL[f];
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
  const [filter, setFilter] = useState<Filter>("all");
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

  // Trigger archive load when Sent filter is selected
  useEffect(() => {
    if (filter === "sent") {
      setArchiveState((prev) => (prev.status === "idle" ? { status: "loading" } : prev));
    }
  }, [filter]);

  // Load archive data once triggered
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
  const allPending = ready ? ready.briefings.filter((b) => b.status === "ready") : [];
  const visiblePending =
    filter === "all" || filter === "sent"
      ? allPending
      : allPending.filter((b) => b.autonomy === filter);
  const archiveBriefings = archiveState.status === "ready" ? archiveState.briefings : [];
  const selected =
    ready && route.name === "briefing"
      ? (ready.briefings.find((b) => b.id === route.id) ?? archiveBriefings.find((b) => b.id === route.id))
      : undefined;

  function countFor(f: Filter): number | null {
    if (f === "sent") return null;
    if (f === "all") return allPending.length;
    return allPending.filter((b) => b.autonomy === f).length;
  }

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
            <p className="subtitle">
              {allPending.length === 0
                ? "All caught up."
                : `${allPending.length} ${allPending.length === 1 ? "briefing" : "briefings"} prepared before you logged in.`}
            </p>
            <div className="segmented" role="tablist" aria-label="Filter queue">
              {FILTERS.map((f) => {
                const n = countFor(f);
                return (
                  <button
                    key={f}
                    type="button"
                    role="tab"
                    aria-selected={filter === f}
                    className="segmented__item"
                    onClick={() => setFilter(f)}
                  >
                    {filterLabel(f)}
                    {n !== null && <span className="segmented__count">{n}</span>}
                  </button>
                );
              })}
            </div>

            {filter !== "sent" && (
              <QueueList
                briefings={visiblePending}
                onOpen={(id) => go(`#/b/${encodeURIComponent(id)}`)}
              />
            )}

            {filter === "sent" && (
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
