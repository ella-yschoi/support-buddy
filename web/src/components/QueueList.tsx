import {
  SEVERITY_LABEL,
  capitalize,
  categoryLabel,
  displayTitle,
  formatTime,
  needsAttention,
  verdict,
} from "../format";
import type { Briefing } from "../types";
import { AutonomyPill } from "./AutonomyPill";

interface Props {
  briefings: Briefing[];
  onOpen: (id: string) => void;
}

export function QueueList({ briefings, onOpen }: Props) {
  if (briefings.length === 0) {
    return <p className="empty">No briefings in this view.</p>;
  }

  return (
    <ul className="group">
      {briefings.map((b) => (
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
  );
}
