#!/bin/bash
# Setup implementation plan for a feature
# Equivalent to setup-plan.ps1 for macOS/Linux environments

set -e

# Default values
JSON_OUTPUT=false
SHOW_HELP=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -json|--json)
            JSON_OUTPUT=true
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
    cat <<EOF
Usage: ./setup-plan.sh [-json] [-help]
  -json     Output results in JSON format
  -help     Show this help message
EOF
    exit 0
fi

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Get all paths and variables
eval "$(get_feature_paths_env)"

# Check if we're on a proper feature branch (only for git repos)
if ! test_feature_branch "$CURRENT_BRANCH" "$HAS_GIT"; then
    exit 1
fi

# Ensure the feature directory exists
mkdir -p "$FEATURE_DIR"

# Copy plan template if it exists, otherwise create empty file
TEMPLATE="$REPO_ROOT/.specify/templates/plan-template.md"
if [[ -f "$TEMPLATE" ]]; then
    cp "$TEMPLATE" "$IMPL_PLAN"
    echo "Copied plan template to $IMPL_PLAN"
else
    echo "Plan template not found at $TEMPLATE" >&2
    # Create a basic plan file if template doesn't exist
    touch "$IMPL_PLAN"
fi

# Output results
if [[ "$JSON_OUTPUT" == "true" ]]; then
    cat <<EOF
{"FEATURE_SPEC":"$FEATURE_SPEC","IMPL_PLAN":"$IMPL_PLAN","SPECS_DIR":"$FEATURE_DIR","BRANCH":"$CURRENT_BRANCH","HAS_GIT":"$HAS_GIT"}
EOF
else
    echo "FEATURE_SPEC: $FEATURE_SPEC"
    echo "IMPL_PLAN: $IMPL_PLAN"
    echo "SPECS_DIR: $FEATURE_DIR"
    echo "BRANCH: $CURRENT_BRANCH"
    echo "HAS_GIT: $HAS_GIT"
fi
