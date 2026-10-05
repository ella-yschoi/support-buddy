import { useState } from "react";
import {
  SEVERITY_LABEL,
  capitalize,
  categoryLabel,
  displayTitle,
  formatTime,
  needsAttention,
  safeTicketUrl,
  sourceLabel,
  verdict,
} from "../format";
import type { Briefing, Hypothesis } from "../types";
import { AutonomyPill } from "./AutonomyPill";
import { ReplyEditor } from "./ReplyEditor";
import { VerificationStrip } from "./VerificationStrip";

interface Props {
  briefing: Briefing;
  onBack: () => void;
  readOnly?: boolean;
  onApproved?: (briefing: Briefing) => void;
}

function HypothesisItem({ hypothesis }: { hypothesis: Hypothesis }) {
  const [open, setOpen] = useState(false);
  const hasEvidence = hypothesis.log_evidence.length > 0 || hypothesis.kb_evidence.length > 0;
  return (
    <li className="hypothesis">
      <p className="hypothesis__statement">{hypothesis.statement}</p>
      {hasEvidence && (
        <button type="button" className="link" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          {open ? "Hide evidence" : "Show evidence"}
        </button>
      )}
      {open && (
        <div className="evidence">
          {hypothesis.log_evidence.length > 0 && (
            <>
              <h4>From the logs</h4>
              <ul>
                {hypothesis.log_evidence.map((line) => (
                  <li key={line}>
                    <code>{line}</code>
                  </li>
                ))}
              </ul>
            </>
          )}
          {hypothesis.kb_evidence.length > 0 && (
            <>
              <h4>From the knowledge base</h4>
              <ul>
                {hypothesis.kb_evidence.map((title) => (
                  <li key={title}>{title}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </li>
  );
}

export function BriefingDetail({ briefing: b, onBack, readOnly = true, onApproved = () => {} }: Props) {
  const attention = needsAttention(b);
  const ticketUrl = b.origin ? safeTicketUrl(b.origin.url) : null;
  return (
    <article className="detail">
      <button type="button" className="back" onClick={onBack}>
        <span aria-hidden="true">‹</span> Queue
      </button>

      <header className="detail__header">
        <h1>{displayTitle(b.inquiry_text)}</h1>
        <p className="detail__meta">
          {capitalize(b.customer_plan)} · {categoryLabel(b.category)} · {SEVERITY_LABEL[b.effective_severity]}{" "}
          severity · {formatTime(b.created_at)}
        </p>
        {ticketUrl && b.origin && (
          <a className="ticket-link" href={ticketUrl} target="_blank" rel="noopener noreferrer">
            Open {b.origin.key} in {sourceLabel(b.origin.source)} <span aria-hidden="true">↗</span>
          </a>
        )}
        <div className="detail__verdict">
          <AutonomyPill level={b.autonomy} simulated={b.simulated} />
          <span className={attention ? "row__verdict row__verdict--attention" : "row__verdict"}>
            {verdict(b)}
          </span>
        </div>
      </header>

      {b.sufficiency === "insufficient" && (
        <section className="notice" aria-label="Briefing is incomplete">
          <p className="notice__title">Start from the raw logs.</p>
          <ul>
            {b.sufficiency_reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="card" aria-label="Customer message">
        <h2>Customer message</h2>
        <p className="quote">{b.inquiry_text}</p>
      </section>

      <section className="card" aria-label="Why this routing">
        <h2>Why this routing</h2>
        <ul className="plain">
          {b.autonomy_reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>

      {b.hypotheses.length > 0 && (
        <section className="card" aria-label="Likely causes">
          <h2>Likely causes</h2>
          <ol className="plain">
            {b.hypotheses.map((h) => (
              <HypothesisItem key={h.statement} hypothesis={h} />
            ))}
          </ol>
        </section>
      )}

      <section className="card" aria-label="Reply">
        <h2>{b.status === "approved" ? "Sent reply" : "Draft reply"}</h2>
        {b.draft_body === null && b.status !== "approved" && (
          <p className="muted">No customer-facing draft. This one needs a person.</p>
        )}
        <ReplyEditor key={b.id + b.status} briefing={b} readOnly={readOnly} onApproved={onApproved} />
        {b.citations.length > 0 && (
          <p className="muted small">Sources: {b.citations.map((c) => c.title).join(" · ")}</p>
        )}
      </section>

      <section className="card" aria-label="Verification">
        <h2>Verification</h2>
        <VerificationStrip checks={b.checks} score={b.verification_score} />
      </section>
    </article>
  );
}
