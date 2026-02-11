# PayLash Future Feature Plan

## Current status (rough)
- **Core split workflow works**: create groups, add members, add shared expenses, and see balances.
- **UX recently improved**: inline buttons and custom IDs reduce friction.
- **Overall completion estimate**: **~55% to a production-ready bot**.

## What is already done
- User registration on `/start`
- Group creation and member linking
- Equal split expense creation
- Basic per-user balance view
- Inline keyboard shortcuts
- Custom user ID support for adding members

## What is still missing before "finished"

### 1) Reliability & correctness (high priority)
- Better input validation for amounts and text edge cases
- Safer error handling and user-friendly failure messages
- Idempotency/duplicate protection for repeated taps
- Transaction and integrity checks for all multi-step actions

### 2) Product completeness (high priority)
- Group-level balance summaries
- Settle-up flow (`mark paid` / `request payment`)
- Expense editing/deletion with audit trail
- Unequal splits (percentages, exact amounts, shares)
- Multi-currency support with conversion logic

### 3) User experience (medium priority)
- Full button-first flows (no fallback commands needed)
- Better onboarding and contextual help
- Member search/autocomplete by custom ID
- Pagination for large groups and long histories

### 4) Admin and operations (medium priority)
- Centralized structured logging
- Metrics/health checks
- Backup and restore strategy
- Migrations/versioning strategy and CI checks

### 5) Security & compliance (medium priority)
- Token/secrets hygiene and rotation support
- Rate limiting / abuse protections
- Privacy controls (data export/delete on request)

## Suggested delivery roadmap

### Milestone A (1-2 weeks): Core hardening
- Validation sweep
- Better callback reliability
- Improved errors and tests

### Milestone B (2-3 weeks): Financial completeness
- Unequal splits
- Edit/delete expense
- Group summary + settle-up basics

### Milestone C (1-2 weeks): Production readiness
- Observability
- Deployment automation
- Data lifecycle tooling

## Definition of "finished" (v1)
A "finished" v1 should have:
1. Stable end-to-end group/expense flows,
2. Clear settle-up experience,
3. Low support burden through validation + observability,
4. Safe upgrade/migration path.
