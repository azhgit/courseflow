---
description: Create or update the project constitution from interactive or provided principle inputs, ensuring all dependent templates stay in sync.
handoffs: 
  - label: Build Specification
    agent: speckit.specify
    prompt: Implement the feature specification based on the updated constitution. I want to build...
---

## Available Tools & Skills

### MCP Servers
- **filesystem**: All constitution and template read/write operations — ALWAYS use instead of native file tools
- **memory**: Write constitution principles summary for all downstream agents to reference

### Skills
- **using-superpowers**: MUST invoke at agent startup
- **senior-architect**: MUST invoke before Step 3 — guides principle definition and governance structure
- **architecture-patterns**: Invoke during Step 3 — ensures principles align with proven architectural patterns (Clean Architecture, DDD, Hexagonal)
- **microservices-patterns**: Invoke during Step 3 if project involves distributed systems — ensures principles cover service boundaries, resilience, and event-driven constraints

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

You are updating the project constitution at `.specify/memory/constitution.md`. This file is a TEMPLATE containing placeholder tokens in square brackets (e.g. `[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`). Your job is to (a) collect/derive concrete values, (b) fill the template precisely, and (c) propagate any amendments across dependent artifacts.

### Startup Sequence (run once before Step 1)

0. **Initialize**:
   - Invoke `using-superpowers` skill to establish available tool context
   - Query `memory` MCP for key `constitution:version`:
     - If exists: display prior version info and ask user if this is an amendment or full rewrite
     - If not exists: proceed as fresh constitution session

---

Follow this execution flow:

1. Use `filesystem` MCP to load the existing constitution template at `.specify/memory/constitution.md`.
   - Identify every placeholder token of the form `[ALL_CAPS_IDENTIFIER]`.
   **IMPORTANT**: The user might require less or more principles than the ones used in the template. If a number is specified, respect that - follow the general template. You will update the doc accordingly.

2. Collect/derive values for placeholders:
   - If user input (conversation) supplies a value, use it.
   - Otherwise infer from existing repo context (README, docs, prior constitution versions if embedded).
   - Use `filesystem` MCP to read README and any existing docs for context inference.
   - For governance dates: `RATIFICATION_DATE` is the original adoption date (if unknown ask or mark TODO), `LAST_AMENDED_DATE` is today if changes are made, otherwise keep previous.
   - `CONSTITUTION_VERSION` must increment according to semantic versioning rules:
     - MAJOR: Backward incompatible governance/principle removals or redefinitions.
     - MINOR: New principle/section added or materially expanded guidance.
     - PATCH: Clarifications, wording, typo fixes, non-semantic refinements.
   - If version bump type ambiguous, propose reasoning before finalizing.

3. **Before drafting — invoke architecture skills**:

   a. Invoke `senior-architect` skill to:
      - Evaluate whether the proposed principles form a coherent, non-contradictory governance system
      - Identify gaps in coverage (e.g., missing observability, security, or testing discipline principles)
      - Ensure each principle is declarative and testable rather than aspirational

   b. Invoke `architecture-patterns` skill to:
      - Verify principles align with the project's chosen architectural style (Clean Architecture, DDD, Hexagonal, etc.)
      - Flag any principles that conflict with the patterns the project has adopted

   c. If project involves microservices or distributed systems, invoke `microservices-patterns` skill to:
      - Ensure principles cover service boundary definitions, event-driven communication contracts, and resilience expectations
      - Add MUST statements for circuit breakers, idempotency, and observability if absent

   Only proceed to drafting after skill outputs have been incorporated.

   Draft the updated constitution content:
   - Replace every placeholder with concrete text (no bracketed tokens left except intentionally retained template slots that the project has chosen not to define yet—explicitly justify any left).
   - Preserve heading hierarchy and comments can be removed once replaced unless they still add clarifying guidance.
   - Ensure each Principle section: succinct name line, paragraph (or bullet list) capturing non‑negotiable rules, explicit rationale if not obvious.
   - Ensure Governance section lists amendment procedure, versioning policy, and compliance review expectations.

4. Consistency propagation checklist — use `filesystem` MCP for all reads:
   - Read `.specify/templates/plan-template.md` and ensure any "Constitution Check" or rules align with updated principles.
   - Read `.specify/templates/spec-template.md` for scope/requirements alignment—update if constitution adds/removes mandatory sections or constraints.
   - Read `.specify/templates/tasks-template.md` and ensure task categorization reflects new or removed principle-driven task types (e.g., observability, versioning, testing discipline).
   - Read each command file in `.specify/templates/commands/*.md` (including this one) to verify no outdated references (agent-specific names like CLAUDE only) remain when generic guidance is required.
   - Read any runtime guidance docs (e.g., `README.md`, `docs/quickstart.md`, or agent-specific guidance files if present). Update references to principles changed.
   - Use `filesystem` MCP for all writes when updating templates.

5. Produce a Sync Impact Report (prepend as an HTML comment at top of the constitution file after update):
   - Version change: old → new
   - List of modified principles (old title → new title if renamed)
   - Added sections
   - Removed sections
   - Templates requiring updates (✅ updated / ⚠ pending) with file paths
   - Follow-up TODOs if any placeholders intentionally deferred.

6. Validation before final output:
   - No remaining unexplained bracket tokens.
   - Version line matches report.
   - Dates ISO format YYYY-MM-DD.
   - Principles are declarative, testable, and free of vague language ("should" → replace with MUST/SHOULD rationale where appropriate).

7. Use `filesystem` MCP to write the completed constitution back to `.specify/memory/constitution.md` (overwrite).

7a. **Persist constitution summary to `memory` MCP** (for all downstream agents):
   - Write to key `constitution:version` with the following structure:
     ```json
     {
       "version": "<X.Y.Z>",
       "ratification_date": "<YYYY-MM-DD>",
       "last_amended": "<YYYY-MM-DD>",
       "project_name": "<name>",
       "must_principles": [
         { "name": "<principle>", "summary": "<one-line rule>" }
       ],
       "architectural_style": "<Clean Architecture / Hexagonal / Microservices / etc>",
       "key_constraints": ["<constraint 1>", "<constraint 2>"]
     }
     ```
   - This allows `speckit.clarify`, `speckit.specify`, `speckit.plan`, `speckit.analyze`, and `speckit.implement` to enforce constitution principles without re-reading the full file each time.

8. Output a final summary to the user with:
   - New version and bump rationale.
   - Any files flagged for manual follow-up.
   - Suggested commit message (e.g., `docs: amend constitution to vX.Y.Z (principle additions + governance update)`).

---

## Formatting & Style Requirements

- Use Markdown headings exactly as in the template (do not demote/promote levels).
- Wrap long rationale lines to keep readability (<100 chars ideally) but do not hard enforce with awkward breaks.
- Keep a single blank line between sections.
- Avoid trailing whitespace.

If the user supplies partial updates (e.g., only one principle revision), still perform validation and version decision steps.

If critical info missing (e.g., ratification date truly unknown), insert `TODO(<FIELD_NAME>): explanation` and include in the Sync Impact Report under deferred items.

Do not create a new template; always operate on the existing `.specify/memory/constitution.md` file.