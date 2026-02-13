#!/bin/bash
# Common bash functions for Spec-Driven Development workflow
# Equivalent to common.ps1 for macOS/Linux environments

set -e

# Get repository root
get_repo_root() {
    if git rev-parse --show-toplevel 2>/dev/null; then
        return 0
    fi
    # Fallback to script location
    dirname "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
}

# Get current branch
get_current_branch() {
    # First check SPECIFY_FEATURE environment variable
    if [[ -n "$SPECIFY_FEATURE" ]]; then
        echo "$SPECIFY_FEATURE"
        return 0
    fi
    
    # Then check git if available
    if git rev-parse --abbrev-ref HEAD 2>/dev/null; then
        return 0
    fi
    
    # For non-git repos, find latest feature directory
    local repo_root=$(get_repo_root)
    local specs_dir="$repo_root/specs"
    
    if [[ -d "$specs_dir" ]]; then
        local latest_feature=""
        local highest=0
        
        for dir in "$specs_dir"/*; do
            if [[ -d "$dir" ]]; then
                local name=$(basename "$dir")
                if [[ "$name" =~ ^([0-9]{3})- ]]; then
                    local num="${BASH_REMATCH[1]}"
                    if (( num > highest )); then
                        highest=$num
                        latest_feature="$name"
                    fi
                fi
            fi
        done
        
        if [[ -n "$latest_feature" ]]; then
            echo "$latest_feature"
            return 0
        fi
    fi
    
    # Final fallback
    echo "main"
}

# Test if git is available
test_has_git() {
    git rev-parse --show-toplevel 2>/dev/null >/dev/null && return 0 || return 1
}

# Validate feature branch naming
test_feature_branch() {
    local branch="$1"
    local has_git="$2"
    
    if [[ "$has_git" != "true" ]]; then
        echo "[specify] Warning: Git repository not detected; skipped branch validation" >&2
        return 0
    fi
    
    if ! [[ "$branch" =~ ^[0-9]{3}- ]]; then
        echo "ERROR: Not on a feature branch. Current branch: $branch" >&2
        echo "Feature branches should be named like: 001-feature-name" >&2
        return 1
    fi
    return 0
}

# Get feature directory
get_feature_dir() {
    local repo_root="$1"
    local branch="$2"
    echo "$repo_root/specs/$branch"
}

# Get all feature paths and environment variables
get_feature_paths_env() {
    local repo_root=$(get_repo_root)
    local current_branch=$(get_current_branch)
    local has_git="false"
    test_has_git && has_git="true"
    local feature_dir=$(get_feature_dir "$repo_root" "$current_branch")
    
    cat <<EOF
REPO_ROOT=$repo_root
CURRENT_BRANCH=$current_branch
HAS_GIT=$has_git
FEATURE_DIR=$feature_dir
FEATURE_SPEC=$feature_dir/spec.md
IMPL_PLAN=$feature_dir/plan.md
TASKS=$feature_dir/tasks.md
RESEARCH=$feature_dir/research.md
DATA_MODEL=$feature_dir/data-model.md
QUICKSTART=$feature_dir/quickstart.md
CONTRACTS_DIR=$feature_dir/contracts
EOF
}

# Test if file exists
test_file_exists() {
    local path="$1"
    local description="$2"
    
    if [[ -f "$path" ]]; then
        echo "  ✓ $description"
        return 0
    else
        echo "  ✗ $description"
        return 1
    fi
}

# Test if directory has files
test_dir_has_files() {
    local path="$1"
    local description="$2"
    
    if [[ -d "$path" ]] && [[ -n "$(find "$path" -type f -print -quit 2>/dev/null)" ]]; then
        echo "  ✓ $description"
        return 0
    else
        echo "  ✗ $description"
        return 1
    fi
}
