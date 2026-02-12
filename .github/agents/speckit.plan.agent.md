---
description: Execute the implementation planning workflow using the plan template to generate design artifacts.
handoffs: 
  - label: Create Tasks
    agent: speckit.tasks
    prompt: Break the plan into tasks
    send: true
  - label: Create Checklist
    agent: speckit.checklist
    prompt: Create a checklist for the following domain...
---

## Available Tools & Skills

### MCP Servers
- **filesystem**: All file read/write operations — ALWAYS use instead of native file tools
- **memory**: Read prior session context; write plan decisions for downstream agents
- **context7**: MUST invoke before adding any new dependency — resolve correct version and current API syntax
- **brave-search**: Research unknowns in Phase 0 when internal context is insufficient

### Skills
- **using-superpowers**: MUST invoke at agent startup
- **senior-architect**: MUST invoke before Phase 1 design — guides data model, API contracts, and architecture decisions
- **api-design-principles**: MUST invoke before generating API contracts in Phase 1
- **architecture-patterns**: Invoke during Technical Context evaluation — ensures chosen patterns align with constitution

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

### Startup Sequence (run once before Step 1)

0. **Initialize**:
   - Invoke `using-superpowers` skill to establish available tool context
   - Query `memory` MCP for prior session context:
     - Key `constitution:version` → load MUST principles and architectural style to enforce throughout planning
     - Key `clarify:results` → load resolved decisions to avoid re-raising already-answered questions
     - Key `analyze:findings` → load any CRITICAL issues flagged in analysis to ensure plan addresses them
   - Display a brief note of loaded context before proceeding

---

1. **Setup**: Run `.specify/scripts/powershell/setup-plan.ps1 -Json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g `'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).

2. **Load context**: Use `filesystem` MCP to read FEATURE_SPEC and `.specify/memory/constitution.md`. Load IMPL_PLAN template (already copied).
   - Cross-reference constitution MUST principles with `constitution:version` from memory (use memory version if available to avoid re-reading full file)
   - Cross-reference clarified decisions from `clarify:results` memory key

3. **Execute plan workflow**: Follow the structure in IMPL_PLAN template to:
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
   - Invoke `architecture-patterns` skill to validate chosen patterns against constitution architectural style
   - Fill Constitution Check section from constitution
   - Evaluate gates (ERROR if violations unjustified)
   - Phase 0: Generate research.md (resolve all NEEDS CLARIFICATION)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md
   - Phase 1: Update agent context by running the agent script
   - Re-evaluate Constitution Check post-design

4. **Stop and report**: Command ends after Phase 2 planning. Report branch, IMPL_PLAN path, and generated artifacts.

## Phases

### Phase 0: Outline & Research

1. **Extract unknowns from Technical Context**:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task + **invoke `context7` MCP to resolve version before proceeding**
   - For each integration → patterns task

2. **Generate and dispatch research agents**:

   ```text
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
     → Use brave-search MCP if internal context insufficient
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
     → Use context7 MCP to verify current API syntax and version
   ```

3. **Consolidate findings** using `filesystem` MCP to write `research.md`:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]
   - Dependency versions: [resolved via context7]

**Output**: research.md with all NEEDS CLARIFICATION resolved and all dependency versions pinned

### Phase 1: Design & Contracts

**Prerequisites:** `research.md` complete

**Before starting Phase 1 — invoke `senior-architect` skill**:
- Use senior-architect to review the research findings and proposed data model approach
- Ensure the overall design is coherent with the constitution's architectural style
- Identify any design decisions that could create technical debt or violate MUST principles
- Only proceed after senior-architect review is complete

1. **Extract entities from feature spec** → use `filesystem` MCP to write `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** — invoke `api-design-principles` skill before writing any contracts:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns validated by api-design-principles skill
   - Use `filesystem` MCP to write OpenAPI/GraphQL schema to `/contracts/`

3. **Agent context update**:
   - Run `.specify/scripts/powershell/update-agent-context.ps1 -AgentType copilot`
   - These scripts detect which AI agent is in use
   - Update the appropriate agent-specific context file
   - Add only new technology from current plan
   - Preserve manual additions between markers

**Output**: data-model.md, /contracts/*, quickstart.md, agent-specific file

### Phase 1 Completion: Persist Plan Decisions to `memory` MCP

Write to key `plan:decisions` with the following structure:
```json
{
  "session_date": "YYYY-MM-DD",
  "branch": "<BRANCH>",
  "architectural_style": "<chosen pattern>",
  "tech_stack": {
    "<layer>": { "technology": "<name>", "version": "<resolved via context7>" }
  },
  "key_decisions": [
    { "area": "<data-model|api|infra>", "decision": "<what>", "rationale": "<why>" }
  ],
  "constitution_violations_resolved": ["<issue>", ...],
  "artifacts_generated": ["research.md", "data-model.md", "contracts/", "quickstart.md"]
}
```
This allows `speckit.tasks` and `speckit.implement` to generate tasks consistent with the plan decisions without re-reading all artifacts.

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications
- NEVER add a dependency without first resolving its version via `context7` MCP
- All file operations MUST use `filesystem` MCP