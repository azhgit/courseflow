---
description: Execute the implementation plan by processing and executing all tasks defined in tasks.md
---

## Available Tools & Skills

### MCP Servers
- **filesystem**: All file read/write/scan operations — ALWAYS prefer over native file tools
- **sequential**: Multi-file coordinated changes requiring atomicity
- **memory**: Dual purpose — (1) track completed tasks to prevent re-execution, (2) record implementation decisions and architecture choices
- **context7**: Resolve correct library versions and APIs — invoke ONLY when adding a new dependency
- **fetch**: Retrieve external documentation or API specs referenced in plan.md
- **brave-search**: Search for solutions when encountering unresolvable errors
- **github-mcp-server**: Read-only GitHub context when task requires cross-PR or issue reference

### Skills (invoke via skill tool before execution)
- **using-superpowers**: MUST invoke at agent startup — establishes tool discovery
- **brainstorming**: MUST invoke before EACH task begins — explore intent and approach before writing any code
- **systematic-debugging**: MUST invoke before proposing any fix when a task fails
- **frontend-design**: Invoke when task involves UI components, pages, or styling
- **rag-implementation**: Invoke when task involves vector search, embeddings, or LLM retrieval
- **api-design-principles**: Invoke when task involves creating or modifying API endpoints

---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

---

## Outline

### Startup Sequence (run once)

0. **Initialize tools**:
   - Invoke `using-superpowers` skill to establish available tool context
   - Query `memory` MCP for any existing session state:
     - Key `implement:completed_tasks` → list of already-completed task IDs (skip these)
     - Key `implement:decisions` → prior architecture decisions to remain consistent with
   - If session state exists, display a resume summary and confirm with user before proceeding

---

1. Run `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g `'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).

2. **Check checklists status** (if FEATURE_DIR/checklists/ exists):
   - Use `filesystem` MCP to scan all checklist files in the checklists/ directory
   - For each checklist, count:
     - Total items: All lines matching `- [ ]` or `- [X]` or `- [x]`
     - Completed items: Lines matching `- [X]` or `- [x]`
     - Incomplete items: Lines matching `- [ ]`
   - Create a status table:

     ```text
     | Checklist   | Total | Completed | Incomplete | Status |
     |-------------|-------|-----------|------------|--------|
     | ux.md       | 12    | 12        | 0          | ✓ PASS |
     | test.md     | 8     | 5         | 3          | ✗ FAIL |
     | security.md | 6     | 6         | 0          | ✓ PASS |
     ```

   - **If any checklist is incomplete**:
     - Display the table with incomplete item counts
     - **STOP** and ask: "Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
     - Wait for user response before continuing
     - If user says "no" or "wait" or "stop", halt execution
     - If user says "yes" or "proceed" or "continue", proceed to step 3

   - **If all checklists are complete**:
     - Display the table showing all checklists passed
     - Automatically proceed to step 3

3. Load and analyze the implementation context using `filesystem` MCP:
   - **REQUIRED**: Read tasks.md for the complete task list and execution plan
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
   - **IF EXISTS**: Read data-model.md for entities and relationships
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements
   - **IF EXISTS**: Read research.md for technical decisions and constraints
   - **IF EXISTS**: Read quickstart.md for integration scenarios

4. **Project Setup Verification**:
   - Use `filesystem` MCP to check existence of all config files
   - **REQUIRED**: Create/verify ignore files based on actual project setup:

   **Detection & Creation Logic**:
   - Check if git repo exists → create/verify `.gitignore`
   - Check if `Dockerfile*` exists or Docker in plan.md → create/verify `.dockerignore`
   - Check if `.eslintrc*` exists → create/verify `.eslintignore`
   - Check if `eslint.config.*` exists → ensure `ignores` entries cover required patterns
   - Check if `.prettierrc*` exists → create/verify `.prettierignore`
   - Check if `.npmrc` or `package.json` exists → create/verify `.npmignore` (if publishing)
   - Check if `*.tf` files exist → create/verify `.terraformignore`
   - Check if helm charts present → create/verify `.helmignore`

   **If ignore file already exists**: Verify essential patterns, append missing critical patterns only  
   **If ignore file missing**: Create with full pattern set for detected technology

   **Common Patterns by Technology** (from plan.md tech stack):
   - **Node.js/TypeScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
   - **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
   - **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
   - **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
   - **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
   - **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
   - **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
   - **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.log`, `.env*`
   - **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
   - **Universal**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

5. Parse tasks.md structure and extract:
   - **Task phases**: Setup, Tests, Core, Integration, Polish
   - **Task dependencies**: Sequential vs parallel execution rules
   - **Task details**: ID, description, file paths, parallel markers `[P]`
   - **Execution flow**: Order and dependency requirements
   - **Skip already-completed**: Cross-reference with `memory` MCP key `implement:completed_tasks`

6. Execute implementation following the task plan:

   **Per-task execution sequence**:

   ```
   For each task:
     a. INVOKE brainstorming skill
        → Explore: What is this task trying to achieve?
        → Explore: What's the simplest correct approach?
        → Explore: What could go wrong?
        → Only proceed to implementation after brainstorming output is clear

     b. IF task adds a new library/package:
        → INVOKE context7 MCP to resolve correct version and current API syntax
        → Record resolved version in memory MCP (key: implement:decisions)

     c. Use filesystem MCP for all file operations
        → For multi-file coordinated changes: use sequential MCP

     d. IF task involves UI components/pages:
        → INVOKE frontend-design skill before writing any markup or styles

     e. IF task involves API endpoints:
        → INVOKE api-design-principles skill before defining routes or contracts

     f. IF task involves RAG, vector search, or LLM integration:
        → INVOKE rag-implementation skill before writing retrieval logic

     g. Execute the implementation

     h. On task completion:
        → Mark task as [X] in tasks.md
        → Update memory MCP key implement:completed_tasks with this task ID
        → If an important decision was made, append to memory MCP key implement:decisions

     i. On task failure:
        → INVOKE systematic-debugging skill before proposing any fix
        → If fix requires brave-search, invoke it with specific error context
        → Do NOT mark task as complete until fix is verified
   ```

   - **Phase-by-phase execution**: Complete each phase before moving to the next
   - **Respect dependencies**: Run sequential tasks in order, parallel tasks `[P]` can run together
   - **Follow TDD approach**: Execute test tasks before their corresponding implementation tasks
   - **File-based coordination**: Tasks affecting the same files must run sequentially via sequential MCP
   - **Validation checkpoints**: Verify each phase completion before proceeding

7. Implementation execution rules:
   - **Setup first**: Initialize project structure, dependencies, configuration
   - **Tests before code**: Write tests for contracts, entities, and integration scenarios
   - **Core development**: Implement models, services, CLI commands, endpoints
   - **Integration work**: Database connections, middleware, logging, external services
   - **Polish and validation**: Unit tests, performance optimization, documentation

8. Progress tracking and error handling:
   - Report progress after each completed task
   - Halt execution if any non-parallel task fails
   - For parallel tasks `[P]`, continue with successful tasks, report failed ones
   - Provide clear error messages with context for debugging
   - Suggest next steps if implementation cannot proceed
   - **IMPORTANT**: For completed tasks, mark the task as `[X]` in the tasks file AND update memory MCP

9. Completion validation:
   - Verify all required tasks are completed
   - Check that implemented features match the original specification
   - Validate that tests pass and coverage meets requirements
   - Confirm implementation follows the technical plan
   - Clear `memory` MCP session keys `implement:completed_tasks` and `implement:decisions`
   - Report final status with summary of completed work and key decisions made

---

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/speckit.tasks` first to regenerate the task list.