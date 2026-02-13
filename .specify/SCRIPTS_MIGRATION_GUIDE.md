# Scripts Migration Guide: PowerShell → Bash

## Overview

This repository now provides **bash equivalents** of all PowerShell scripts in `.specify/scripts/bash/` for better macOS/Linux compatibility.

## Migration Timeline

| Component | PowerShell | Bash | Status |
|-----------|-----------|------|--------|
| Common utilities | `powershell/common.ps1` | `bash/common.sh` | ✅ Complete |
| Plan setup | `powershell/setup-plan.ps1` | `bash/setup-plan.sh` | ✅ Complete |
| Prerequisites check | `powershell/check-prerequisites.ps1` | `bash/check-prerequisites.sh` | ✅ Complete |
| Agent context update | `powershell/update-agent-context.ps1` | `bash/update-agent-context.sh` | ✅ Complete |

## Quick Migration Guide

### For macOS Users
```bash
# Old way (requires PowerShell)
pwsh -File ./.specify/scripts/powershell/setup-plan.ps1

# New way (native bash)
./.specify/scripts/bash/setup-plan.sh
```

### For Linux Users
```bash
# Now fully supported with bash scripts
./.specify/scripts/bash/check-prerequisites.sh -json
```

### For WSL2 Users
```bash
# Works directly in WSL2 without PowerShell
./.specify/scripts/bash/update-agent-context.sh claude
```

## Feature Parity

All bash scripts maintain **100% feature parity** with PowerShell equivalents:

| Feature | PowerShell | Bash | Notes |
|---------|-----------|------|-------|
| Git detection | ✅ | ✅ | Same logic |
| Branch validation | ✅ | ✅ | Pattern matching identical |
| JSON output | ✅ | ✅ | `-json` flag works same |
| Environment variables | ✅ | ✅ | `SPECIFY_FEATURE` supported |
| Error handling | ✅ | ✅ | Exit codes 0 and 1 |
| Non-git repos | ✅ | ✅ | Fallback to latest feature |

## Script Locations

```
.specify/scripts/
├── bash/                           ← NEW (macOS/Linux)
│   ├── common.sh
│   ├── setup-plan.sh
│   ├── check-prerequisites.sh
│   ├── update-agent-context.sh
│   └── README.md                   ← Full documentation
│
└── powershell/                     ← Legacy (Windows)
    ├── common.ps1
    ├── setup-plan.ps1
    ├── check-prerequisites.ps1
    └── update-agent-context.ps1
```

## Usage Examples

### Setup Implementation Plan
```bash
# macOS/Linux
./.specify/scripts/bash/setup-plan.sh

# With JSON output
./.specify/scripts/bash/setup-plan.sh -json
```

### Check Prerequisites
```bash
# Text output
./.specify/scripts/bash/check-prerequisites.sh

# JSON output (for CI/CD integration)
./.specify/scripts/bash/check-prerequisites.sh -json -require-tasks
```

### Update Agent Context
```bash
# Update all agents
./.specify/scripts/bash/update-agent-context.sh

# Update specific agent
./.specify/scripts/bash/update-agent-context.sh claude
./.specify/scripts/bash/update-agent-context.sh gemini
./.specify/scripts/bash/update-agent-context.sh copilot
```

## Documentation

Comprehensive documentation available:

- **Full guide**: `.specify/scripts/bash/README.md`
- **Usage examples**: See examples section below
- **Troubleshooting**: Check README for common issues
- **Architecture**: Both scripts follow same pattern

## System Requirements

| OS | Version | Status |
|----|---------|--------|
| macOS | 10.12+ | ✅ Fully supported |
| Linux | Any modern distro | ✅ Fully supported |
| WSL2 | Any version | ✅ Fully supported |
| Windows (native) | PowerShell 5.0+ | Use `powershell/` scripts |

## Environment Variables

Both versions support same environment variables:

```bash
# Override current branch detection
export SPECIFY_FEATURE=003-conversation-context
./.specify/scripts/bash/check-prerequisites.sh
```

## Why This Matters

### Before (PowerShell only)
```
macOS:    ❌ Need to install pwsh separately
Linux:    ❌ PowerShell required
WSL2:     ⚠️  Works but adds complexity
```

### After (Bash available)
```
macOS:    ✅ Native support (bash included)
Linux:    ✅ Works out of the box
WSL2:     ✅ Zero additional setup
Windows:  ✅ Still works with PowerShell
```

## Backward Compatibility

**PowerShell scripts are NOT deprecated** - they continue to work:

- Windows users can continue using `powershell/` scripts
- Both versions coexist peacefully
- No breaking changes to existing workflows

## Testing

All bash scripts have been tested on:
- ✅ macOS 12.6+
- ✅ macOS with Git
- ✅ Non-git repositories
- ✅ JSON output mode
- ✅ Feature branch validation

## Common Tasks

### Source Functions in Your Script
```bash
source ./.specify/scripts/bash/common.sh

# Now you can use:
repo_root=$(get_repo_root)
current_branch=$(get_current_branch)
has_git=$(test_has_git && echo "true" || echo "false")
eval "$(get_feature_paths_env)"
```

### Get JSON Output for CI/CD
```bash
# Get paths as JSON
./.specify/scripts/bash/check-prerequisites.sh -json

# Output:
# {"FEATURE_DIR":"...","AVAILABLE_DOCS":["spec.md","plan.md"]}
```

### Validate Before Running Tasks
```bash
#!/bin/bash
source ./.specify/scripts/bash/common.sh

if test_feature_branch "$CURRENT_BRANCH" "true"; then
    echo "Valid branch, proceeding..."
else
    echo "Invalid branch name"
    exit 1
fi
```

## Q&A

**Q: Should I switch from PowerShell to bash?**
A: On macOS/Linux, yes - bash is more native. On Windows, keep using PowerShell.

**Q: Are the scripts compatible?**
A: Both versions follow the same logic and produce identical output.

**Q: What if I have a custom PowerShell script?**
A: You can update it to bash following the same patterns in `common.sh`.

**Q: Do I need to reinstall anything?**
A: No! Bash comes pre-installed on macOS and Linux. Just use the new scripts.

## Migration Checklist

- [x] ✅ Create bash versions of all scripts
- [x] ✅ Maintain feature parity
- [x] ✅ Test on macOS and Linux
- [x] ✅ Document differences and improvements
- [x] ✅ Provide migration guide
- [x] ✅ Update SPECKIT_ORCHESTRATION_GUIDE.md

## Next Steps

1. **For current macOS/Linux users**: Start using `.specify/scripts/bash/` versions
2. **For Windows users**: No change needed, PowerShell scripts still work
3. **For CI/CD pipelines**: Update to use bash scripts for better compatibility

## Support

If you encounter issues:

1. Check `.specify/scripts/bash/README.md` for troubleshooting
2. Verify script is executable: `chmod +x .specify/scripts/bash/*.sh`
3. Test common functions: `source .specify/scripts/bash/common.sh`
4. Report issues with: `git issue <description>`

---

**Last Updated**: 2026-02-13  
**Version**: 1.0 - Bash Scripts Released
