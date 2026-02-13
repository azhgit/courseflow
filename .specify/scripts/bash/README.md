# Bash Scripts for Spec-Driven Development (macOS/Linux)

This directory contains bash equivalents of the PowerShell scripts in `../powershell/`, optimized for macOS, Linux, and Unix-like environments.

## 📋 Files Overview

| Script | Purpose | Equivalent |
|--------|---------|-----------|
| `common.sh` | Shared utility functions | `powershell/common.ps1` |
| `setup-plan.sh` | Initialize implementation plan structure | `powershell/setup-plan.ps1` |
| `check-prerequisites.sh` | Validate feature requirements | `powershell/check-prerequisites.ps1` |
| `update-agent-context.sh` | Update AI agent context files | `powershell/update-agent-context.ps1` |

## ✅ Compatibility

- **macOS**: ✓ Fully supported (10.12+)
- **Linux**: ✓ Fully supported (any modern distribution)
- **Windows (WSL2)**: ✓ Supported
- **Windows (native PowerShell)**: Use `../powershell/` scripts instead

## 🚀 Quick Start

### 1. Setup Plan
```bash
# From repo root
./.specify/scripts/bash/setup-plan.sh

# With JSON output
./.specify/scripts/bash/setup-plan.sh -json
```

### 2. Check Prerequisites
```bash
# Validate planning phase
./.specify/scripts/bash/check-prerequisites.sh

# Validate implementation phase (requires tasks.md)
./.specify/scripts/bash/check-prerequisites.sh -require-tasks -include-tasks

# Get paths only
./.specify/scripts/bash/check-prerequisites.sh -paths-only
```

### 3. Update Agent Context
```bash
# Update all existing agent files
./.specify/scripts/bash/update-agent-context.sh

# Update specific agent
./.specify/scripts/bash/update-agent-context.sh claude
./.specify/scripts/bash/update-agent-context.sh gemini
./.specify/scripts/bash/update-agent-context.sh copilot
```

## 📖 Usage Examples

### Get Feature Paths
```bash
# Source common functions and get paths
source ./.specify/scripts/bash/common.sh
eval "$(get_feature_paths_env)"

echo "Feature directory: $FEATURE_DIR"
echo "Plan file: $IMPL_PLAN"
echo "Current branch: $CURRENT_BRANCH"
```

### Validate Feature Branch
```bash
source ./.specify/scripts/bash/common.sh
eval "$(get_feature_paths_env)"

if test_feature_branch "$CURRENT_BRANCH" "$HAS_GIT"; then
    echo "Valid feature branch"
else
    echo "Invalid branch name"
    exit 1
fi
```

### Check if on Git Repository
```bash
if test_has_git; then
    echo "Git repository detected"
else
    echo "Not a git repository"
fi
```

## 🔧 Environment Variables

The scripts support the following environment variables:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SPECIFY_FEATURE` | Override current branch detection | `export SPECIFY_FEATURE=003-conversation-context` |

## 📝 JSON Output Format

All scripts support `-json` flag for machine-readable output:

```bash
./check-prerequisites.sh -json
# Output:
# {"FEATURE_DIR":"/path/to/specs/003-feature","AVAILABLE_DOCS":["research.md","data-model.md","contracts/","quickstart.md"]}
```

## 🐛 Troubleshooting

### Script Permission Denied
```bash
# Make scripts executable
chmod +x ./.specify/scripts/bash/*.sh
```

### Command Not Found
```bash
# Use explicit path or add to PATH
./.specify/scripts/bash/setup-plan.sh

# Or
export PATH="$PATH:./.specify/scripts/bash"
setup-plan.sh
```

### Git Detection Issues
```bash
# Set feature name manually
export SPECIFY_FEATURE=003-my-feature
./check-prerequisites.sh
```

## 🔄 Migration from PowerShell

If you were using PowerShell scripts:

| PowerShell | Bash Equivalent |
|-----------|-----------------|
| `.\setup-plan.ps1` | `./.specify/scripts/bash/setup-plan.sh` |
| `.\setup-plan.ps1 -Json` | `./.specify/scripts/bash/setup-plan.sh -json` |
| `.\check-prerequisites.ps1 -Json` | `./.specify/scripts/bash/check-prerequisites.sh -json` |
| `.\update-agent-context.ps1 -AgentType claude` | `./.specify/scripts/bash/update-agent-context.sh claude` |

## 📚 Architecture

All scripts follow a common pattern:

1. **Parse arguments** - Handle CLI flags
2. **Source common.sh** - Load shared functions
3. **Get environment** - Determine repo root, branch, feature directory
4. **Validate** - Check prerequisites and branch naming
5. **Execute** - Perform the main operation
6. **Output** - Return results (text or JSON)

## 🚦 Exit Codes

- `0` - Success
- `1` - Error (invalid branch, missing files, validation failure)

## 🤝 Contributing

When modifying these scripts:

1. Maintain parity with PowerShell equivalents
2. Test on macOS and Linux
3. Use `set -e` to exit on errors
4. Provide both text and JSON output options
5. Document new environment variables
