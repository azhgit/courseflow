# MCP runner commands and examples

This file lists example npx runner commands and exactly where to paste them when creating MCP entries in Copilot CLI (`/mcp add <name>`).

IMPORTANT: Replace placeholders with the actual npx package or command your environment uses. Test runners locally before adding them to Copilot CLI.

Example runner commands (place each full command when prompted by `/mcp add`):

1) sequential (stdio)
# Purpose: Run shell commands or orchestrate tasks sequentially.
# Example (replace with your runner package):
npx @your-org/copilot-mcp-sequential --stdio

2) filesystem (stdio)
# Purpose: Provide safe filesystem access for skills that need to read/write files.
npx @your-org/copilot-mcp-filesystem --stdio --root="/path/to/repo"

3) brave-search (stdio) / fetch (stdio)
# Purpose: Web fetch/search backends used by fetch/brave-search skills.
npx @your-org/copilot-mcp-brave-search --stdio
npx @your-org/copilot-mcp-fetch --stdio

4) memory (stdio)
# Purpose: Long-running memory storage/graph for skills that persist observations.
npx @your-org/copilot-mcp-memory --stdio --db ./data/copilot-memory.db

5) context7 (stdio)
# Purpose: Context enrichment or custom LLM prompt helpers.
npx @your-org/copilot-mcp-context7 --stdio

Notes and tips
- If your runner requires environment variables (e.g., API keys), ensure they are available in the Copilot CLI process environment.
- Use absolute paths for --root or --db flags to avoid ambiguity.
- Test each runner locally by starting the runner and then using the Copilot CLI `/mcp add` interactive flow to paste the command when prompted.

Security checklist before adding a runner
- The runner runs arbitrary code: ensure it is from a trusted package source.
- Limit runner permissions to only needed directories (use --root flags or containerization).
- Do not embed secrets directly in runner commands; use environment variables or CI secret stores.

If you want, I can produce a ready-to-run `copilot` command sequence to add these MCP entries interactively (you will need to paste each runner command when prompted).