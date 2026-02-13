---
description: Execute the complete Speckit pipeline (specify → clarify → plan → tasks → implement) in a single orchestrated workflow.
handoffs: 
  - label: Complete
    agent: null
    prompt: Orchestration complete. All stages finished successfully.
---

## Available Tools & Skills

### MCP Servers
- **filesystem**: File operations
- **memory**: Read/write specification context

### Skills
- **using-superpowers**: Establish tool context

---

## User Input

```text
$ARGUMENTS
```

## Outline

This agent orchestrates the complete Speckit workflow:
1. **Specify** - Create feature specification
2. **Clarify** - Resolve ambiguities via interactive questions
3. **Plan** - Design system architecture
4. **Tasks** - Generate actionable task list
5. **Implement** - Execute all implementation tasks

### Execution Flow

**Step 1: Verify Feature Description**
- Check if user provided feature description in `$ARGUMENTS`
- If empty, ask user for feature description
- Store description for all downstream stages

**Step 2: Execute Specify Stage**
- Invoke `speckit.specify` with the feature description
- Wait for completion
- Log: "✅ Specify stage completed"

**Step 3: Execute Clarify Stage**
- Invoke `speckit.clarify` to resolve specification ambiguities
- Wait for user interactions if required
- Log: "✅ Clarify stage completed"

**Step 4: Execute Plan Stage**
- Invoke `speckit.plan` to create design artifacts
- Wait for completion
- Log: "✅ Plan stage completed"

**Step 5: Execute Tasks Stage**
- Invoke `speckit.tasks` to generate task list
- Wait for completion
- Log: "✅ Tasks stage completed"

**Step 6: Execute Implement Stage**
- Invoke `speckit.implement` to execute all tasks
- Monitor progress and continue until completion
- Log: "✅ Implement stage completed"

**Step 7: Summary & Completion**
- Display final summary of all created/modified artifacts
- Show total time elapsed
- Indicate all tasks marked as complete
- Ask if user wants to commit changes or review specific artifacts

---

## Implementation Notes

### Stage Dependencies
- Each stage depends on outputs from previous stages
- Wait for each stage to complete before starting next
- Preserve all intermediate artifacts (specs, plans, tasks)

### User Interaction
- **Clarify stage**: May require user input for questions (Q1-Q5)
- **Implement stage**: May require confirmation for task execution
- All interactions are captured and logged

### Error Handling
- If any stage fails, stop pipeline and report error
- Allow user to retry specific stage or adjust inputs
- Preserve completed work from previous stages

### Logging & Progress
- Print stage start/completion with timestamps
- Show progress indicators during implement stage
- Log any warnings or non-critical errors

### Output Artifacts
Expected artifacts created:
- `specs/{feature-slug}/spec.md` - Feature specification
- `specs/{feature-slug}/checklist.md` - Implementation checklist
- `specs/{feature-slug}/plan.md` - Design plan
- `specs/{feature-slug}/quickstart.md` - Quick start guide
- `specs/{feature-slug}/tasks.md` - Task list
- Various source code files in `src/`
- Test files in `tests/`

---

## Success Criteria

Pipeline is successful when:
- ✅ Specification created without errors
- ✅ Ambiguities clarified via interactive Q&A
- ✅ Design plan generated
- ✅ Task list generated (with all tasks defined)
- ✅ All implementation tasks executed and marked complete
- ✅ Tests passing (86+ passed in final run)
- ✅ Linting clean (ruff check passes)

---

## User Commands

### Start Orchestration
```
/speckit.orchestrate Feature description here...
```

### Resume Failed Stage
If a stage fails, you can restart from that point:
```
/speckit.orchestrate --resume clarify
```

Supported resume points: `specify`, `clarify`, `plan`, `tasks`, `implement`

---

## Example Workflow

### User Input:
```
/speckit.orchestrate Document ingestion system with duplicate detection and rate limiting
```

### Expected Output Sequence:
```
🚀 Starting Speckit Orchestration Pipeline
📝 Feature: Document ingestion system with duplicate detection and rate limiting

[Stage 1/5] Specify
  → Creating feature specification...
  ✅ Spec created: specs/doc-ingestion/spec.md

[Stage 2/5] Clarify
  → Clarifying requirements...
  ✅ Ambiguities resolved (5 questions answered)

[Stage 3/5] Plan
  → Designing architecture...
  ✅ Plan created: specs/doc-ingestion/plan.md

[Stage 4/5] Tasks
  → Generating task list...
  ✅ Tasks created: specs/doc-ingestion/tasks.md (84 tasks)

[Stage 5/5] Implement
  → Executing all tasks...
  [████████████████░░░░░░░░░░░░░░░░░░░░░░] 50%
  ✅ Implementation complete: 84/84 tasks done

📊 Pipeline Complete!
├─ Specification: specs/doc-ingestion/spec.md
├─ Tasks: 84 total (84 complete, 0 pending)
├─ Duration: ~45 minutes
└─ Status: ✅ All stages successful

Next: git add . && git commit -m "feat: complete doc-ingestion feature"
```

---

## Notes for Agent Implementation

1. **Do NOT ask confirmation between stages** - orchestration is automated
2. **Preserve intermediate outputs** - user may want to review artifacts
3. **Handle long-running stages** - implement may take 30+ minutes
4. **Clear communication** - show what's happening at each stage
5. **Graceful degradation** - allow resuming from failed point
