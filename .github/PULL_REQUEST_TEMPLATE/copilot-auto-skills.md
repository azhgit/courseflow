# PR: Enable/Run Copilot Auto-Skills

This PR was generated to enable or execute authorized Copilot MCP/skills actions. It contains the changes produced by the Assistant and a run summary.

## What this PR does
- [ ] Installs/enables the following skills: `{{skills}}`
- [ ] Registers the following MCP servers: `{{mcp_servers}}` (runner commands provided)
- [ ] Applies changes to files: `{{files_changed}}`

## Why
This PR was created to automate repetitive tasks (documentation updates, code scaffolding, refactors, or CI improvements) using authorized Copilot skills. See `.github/copilot-allow.yml` for allowed skills and MCP servers.

## Run summary (to be filled by Assistant)
- Date: {{date}}
- Command summary: 
  - `/skills add ...`
  - `/mcp add ...`
- Output excerpt: (first 2000 chars)

## Security & Review checklist
- [ ] No credentials or secrets are added to repository files
- [ ] All third-party packages and runners are from trusted sources
- [ ] require_manual_confirm is enabled or explicit approval recorded
- [ ] Changes are covered by unit/integration tests where applicable

## How to test
1. Follow the PR diff and run tests locally: `pytest -q`
2. Manually inspect installed skills: `copilot /skills list`
3. Verify MCP registration: `copilot /mcp show`

## Rollback
If anything unexpected happens, revert this PR or run:
```
# Disable skills
copilot -i "/skills remove <name>"
# Remove MCP entries
copilot -i "/mcp delete <server-name>"
```

---

Please review and merge if everything looks good. The Assistant recorded the full run log in `.github/copilot-auto-skills-runs.log` (if enabled in allow file).
