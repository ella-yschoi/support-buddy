import { useState } from "react";
import { deleteBriefing } from "../api";
import { SEVERITY_LABEL, capitalize, categoryLabel, displayTitle, formatTime } from "../format";
import type { Briefing } from "../types";

interface Props {
  briefings: Briefing[];
  onOpen: (id: string) => void;
  onDeleted: (id: string) => void;
}

export function ArchiveList({ briefings, onOpen, onDeleted }: Props) {
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (briefings.length === 0) {
    return <p className="empty">No archived briefings yet. Sent replies appear here.</p>;
  }

  async function handleDelete(id: string) {
    setDeleting(id);
    setError(null);
    try {
      await deleteBriefing(id);
      onDeleted(id);
    } catch {
      setError("Couldn't delete the briefing. Try again.");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div>
      {error && (
        <p role="alert" className="notice">
          {error}
        </p>
      )}
      <ul className="group">
        {briefings.map((b) => (
          <li key={b.id} className="row row--archive">
            <button
              type="button"
              className="row row--archive__main"
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
              </span>
            </button>
            <button
              type="button"
              className="btn btn--danger btn--sm"
              disabled={deleting === b.id}
              onClick={() => handleDelete(b.id)}
            >
              {deleting === b.id ? "Deleting…" : "Delete permanently"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
