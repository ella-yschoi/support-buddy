export type Autonomy = "auto" | "confirm" | "human_only";
export type Severity = "low" | "medium" | "high" | "critical";
export type Sufficiency = "sufficient" | "insufficient";

export interface Hypothesis {
  statement: string;
  log_evidence: string[];
  kb_evidence: string[];
}

export interface Check {
  name: string;
  passed: boolean;
  detail: string;
}

export interface Briefing {
  id: string;
  created_at: string;
  inquiry_text: string;
  customer_plan: string;
  summary: string;
  category: string;
  model_severity: Severity;
  effective_severity: Severity;
  hypotheses: Hypothesis[];
  citations: { doc_id: string; title: string }[];
  checks: Check[];
  verification_score: number;
  verification_passed: boolean;
  autonomy: Autonomy;
  autonomy_reasons: string[];
  simulated: boolean;
  draft_body: string | null;
  sufficiency: Sufficiency;
  sufficiency_reasons: string[];
  status: string;
  approved_body: string | null;
  edit_ratio: number | null;
}

export type Source = "api" | "demo";

export type Plan = "unknown" | "free" | "pro" | "enterprise";
