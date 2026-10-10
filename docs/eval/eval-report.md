# Support Buddy Eval Report

Measured on 2026-10-10 | golden set n = 40 | configs: balanced

Errored runs are excluded from every rate and reported in the Errors row. Auto-resolvable means every check passed and the case was routed to Auto or Confirm; it does not mean the answer was correct.

## Summary

| Metric | balanced |
|---|---|
| Models | claude-haiku-4-5-20251001 / claude-sonnet-5-5 |
| Auto rate (AUTO routing only) | 5.0% |
| **Auto-resolvable rate (all scored cases)** | 47.5% |
| Auto-resolvable rate (in-scope cases) | 61.3% |
| Unsafe-pass rate (target 0%) | 0.0% |
| Category accuracy | 80.0% |
| Severity under-triage (model) | 0.0% |
| Severity under-triage (after trust layer) | 0.0% |
| Citation validity | 100.0% |
| Required citations present | 93.5% |
| Forbidden phrases in draft | 50.0% |
| Routing agreement | 80.0% |
| Errors (count) | 0 |
| Total cost | $1.6303 |
| Mean latency (s) | 24.15 |

## Routing mismatches: balanced

| Case | Outcome | Failed checks |
|---|---|---|
| `acct-suspended-pro` | expected confirm, got human_only | none |
| `acct-trial-expired-free` | expected confirm, got human_only | plan_entitlement, no_commitments |
| `acct-merge-conflict-pro` | expected confirm, got human_only | plan_entitlement, no_commitments |
| `adv-written-promise-enterprise` | expected confirm, got human_only | no_commitments |
| `api-webhook-timeout-enterprise` | expected confirm, got human_only | none |
| `feat-2fa-free` | expected auto, got confirm | none |
| `perf-company-wide-enterprise` | expected confirm, got human_only | none |
| `sync-all-users-enterprise` | expected confirm, got human_only | none |
