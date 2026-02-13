#!/bin/bash
# Consolidated prerequisite checking script (bash)
# Equivalent to check-prerequisites.ps1 for macOS/Linux environments

set -e

# Default values
JSON_OUTPUT=false
REQUIRE_TASKS=false
INCLUDE_TASKS=false
PATHS_ONLY=false
SHOW_HELP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -json|--json)
            JSON_OUTPUT=true
            shift
            ;;
        -require-tasks|--require-tasks)
            REQUIRE_TASKS=true
            shift
            ;;
        -include-tasks|--include-tasks)
            INCLUDE_TASKS=true
            shift
            ;;
        -paths-only|--paths-only)
            PATHS_ONLY=true
            shift
            ;;
        -h|-help|--help)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo "Unknown option: $1" >&2
            SHOW_HELP=true
            shift
            ;;
    esac
done

# Show help if requested
if [[ "$SHOW_HELP" == "true" ]]; then
    cat <<'EOF'
Usage: check-prerequisites.sh [OPTIONS]

Consolidated prerequisite checking for Spec-Driven Development workflow.

OPTIONS:
  -json             Output in JSON format
  -require-tasks    Require tasks.md to exist (for implementation phase)
  -include-tasks    Include tasks.md in AVAILABLE_DOCS list
  -paths-only       Only output path variables (no prerequisite validation)
  -help             Show this help message

EXAMPLES:
  # Check task prerequisites (plan.md required)
  ./check-prerequisites.sh -json
  
  # Check implementation prerequisites (plan.md + tasks.md required)
  ./check-prerequisites.sh -json -require-tasks -include-tasks
  
  # Get feature paths only (no validation)
  ./check-prerequisites.sh -paths-only
EOF
    exit 0
fi

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get feature paths and validate branch
eval "$(get_feature_paths_env)"

if ! test_feature_branch "$CURRENT_BRANCH" "$HAS_GIT"; then
    exit 1
fi

# If paths-only mode, output paths and exit (supports combined -json -paths-only)
if [[ "$PATHS_ONLY" == "true" ]]; then
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        cat <<EOF
{"REPO_ROOT":"$REPO_ROOT","BRANCH":"$CURRENT_BRANCH","FEATURE_DIR":"$FEATURE_DIR","FEATURE_SPEC":"$FEATURE_SPEC","IMPL_PLAN":"$IMPL_PLAN","TASKS":"$TASKS"}
EOF
    else
        echo "REPO_ROOT: $REPO_ROOT"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "FEATURE_DIR: $FEATURE_DIR"
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_PLAN: $IMPL_PLAN"
        echo "TASKS: $TASKS"
    fi
    exit 0
fi

# Validate required directories and files
if [[ ! -d "$FEATURE_DIR" ]]; then
    echo "ERROR: Feature directory not found: $FEATURE_DIR" >&2
    echo "Run /speckit.specify first to create the feature structure." >&2
    exit 1
fi

if [[ ! -f "$IMPL_PLAN" ]]; then
    echo "ERROR: plan.md not found in $FEATURE_DIR" >&2
    echo "Run /speckit.plan first to create the implementation plan." >&2
    exit 1
fi

# Check for tasks.md if required
if [[ "$REQUIRE_TASKS" == "true" ]] && [[ ! -f "$TASKS" ]]; then
    echo "ERROR: tasks.md not found in $FEATURE_DIR" >&2
    echo "Run /speckit.tasks first to create the task list." >&2
    exit 1
fi

# Build list of available documents
docs=()

# Always check these optional docs
[[ -f "$RESEARCH" ]] && docs+=('research.md')
[[ -f "$DATA_MODEL" ]] && docs+=('data-model.md')

# Check contracts directory (only if it exists and has files)
if [[ -d "$CONTRACTS_DIR" ]] && [[ -n "$(find "$CONTRACTS_DIR" -type f -print -quit 2>/dev/null)" ]]; then
    docs+=('contracts/')
fi

[[ -f "$QUICKSTART" ]] && docs+=('quickstart.md')

# Include tasks.md if requested and it exists
if [[ "$INCLUDE_TASKS" == "true" ]] && [[ -f "$TASKS" ]]; then
    docs+=('tasks.md')
fi

# Output results
if [[ "$JSON_OUTPUT" == "true" ]]; then
    # Convert array to JSON
    local json_docs="["
    for ((i = 0; i < ${#docs[@]}; i++)); do
        json_docs+="\"${docs[$i]}\""
        if (( i < ${#docs[@]} - 1 )); then
            json_docs+=","
        fi
    done
    json_docs+="]"
    
    cat <<EOF
{"FEATURE_DIR":"$FEATURE_DIR","AVAILABLE_DOCS":$json_docs}
EOF
else
    # Text output
    echo "FEATURE_DIR:$FEATURE_DIR"
    echo "AVAILABLE_DOCS:"
    
    # Show status of each potential document
    test_file_exists "$RESEARCH" 'research.md' || true
    test_file_exists "$DATA_MODEL" 'data-model.md' || true
    test_dir_has_files "$CONTRACTS_DIR" 'contracts/' || true
    test_file_exists "$QUICKSTART" 'quickstart.md' || true
    
    if [[ "$INCLUDE_TASKS" == "true" ]]; then
        test_file_exists "$TASKS" 'tasks.md' || true
    fi
fi
