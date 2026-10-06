import { useState } from "react";
import {
  AUTONOMY_LABEL,
  SEVERITY_LABEL,
  capitalize,
  categoryLabel,
  displayTitle,
  formatTime,
  needsAttention,
  verdict,
} from "../format";
import type { Autonomy, Briefing } from "../types";
import { AutonomyPill } from "./AutonomyPill";

type Filter = "all" | Autonomy;
const FILTERS: Filter[] = ["all", "auto", "confirm", "human_only"];

interface Props {
  briefings: Briefing[];
  onOpen: (id: string) => void;
}

export function QueueList({ briefings, onOpen }: Props) {
  const [filter, setFilter] = useState<Filter>("all");
  const count = (f: Filter) =>
    f === "all" ? briefings.length : briefings.filter((b) => b.autonomy === f).length;
  const visible = filter === "all" ? briefings : briefings.filter((b) => b.autonomy === filter);

  if (briefings.length === 0) {
    return <p className="empty">Nothing waiting. Briefings appear here as tickets arrive.</p>;
  }

  return (
    <div>
      <div className="segmented" role="tablist" aria-label="Filter by autonomy level">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            role="tab"
            aria-selected={filter === f}
            className="segmented__item"
            onClick={() => setFilter(f)}
          >
            {f === "all" ? "All" : AUTONOMY_LABEL[f]} <span className="segmented__count">{count(f)}</span>
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <p className="empty">No briefings in this view.</p>
      ) : (
        <ul className="group">
          {visible.map((b) => (
            <li key={b.id}>
              <button
                type="button"
                className="row"
                aria-label={`Open briefing: ${displayTitle(b.inquiry_text)}`}
                onClick={() => onOpen(b.id)}
              >
                <span
                  className={`severity severity--${b.effective_severity}`}
                  role="img"
                  aria-label={`${SEVERITY_LABEL[b.effective_severity]} severity`}
                />
                <span className="row__body">
                  <span role="heading" aria-level={3} className="row__title">
                    {displayTitle(b.inquiry_text)}
                  </span>
                  <span className="row__meta">
                    {b.origin ? `${b.origin.key} · ` : ""}
                    {capitalize(b.customer_plan)} · {categoryLabel(b.category)} · {formatTime(b.created_at)}
                  </span>
                  <span className={`row__verdict${needsAttention(b) ? " row__verdict--attention" : ""}`}>
                    {verdict(b)}
                  </span>
                </span>
                <AutonomyPill level={b.autonomy} simulated={b.simulated} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
