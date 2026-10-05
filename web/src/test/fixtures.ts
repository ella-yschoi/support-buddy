import type { Briefing } from "../types";

export function makeBriefing(overrides: Partial<Briefing> = {}): Briefing {
  return {
    id: "b-1",
    created_at: "2026-10-04T02:00:00",
    inquiry_text: "Files stopped syncing and I see SYNC-002.",
    customer_plan: "pro",
    summary: "Uploads are failing with a storage error",
    category: "sync",
    model_severity: "medium",
    effective_severity: "medium",
    hypotheses: [
      {
        statement: "Storage quota exceeded",
        log_evidence: ["2026-10-04T01:58:00 ERROR SYNC-002 upload failed"],
        kb_evidence: ["SYNC-002: Upload Failed"],
      },
    ],
    citations: [{ doc_id: "doc-1", title: "SYNC-002: Upload Failed" }],
    checks: [
      { name: "citations_exist", passed: true, detail: "1 sources found" },
      { name: "plan_entitlement", passed: true, detail: "no plan-gated features mentioned" },
    ],
    verification_score: 1,
    verification_passed: true,
    autonomy: "confirm",
    autonomy_reasons: ["Category 'sync' is not auto-eligible"],
    simulated: false,
    draft_body: "Thanks for reaching out. Please check your storage usage.",
    sufficiency: "sufficient",
    sufficiency_reasons: ["Evidence and citations found; verification passed"],
    status: "ready",
    approved_body: null,
    edit_ratio: null,
    origin: null,
    ...overrides,
  };
}
