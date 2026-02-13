#!/bin/bash
# Update agent context files with information from plan.md (bash version)
# Equivalent to update-agent-context.ps1 for macOS/Linux environments

set -e

# Parse arguments
AGENT_TYPE=""
if [[ $# -gt 0 ]]; then
    AGENT_TYPE="$1"
fi

# Import common helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Acquire environment paths
eval "$(get_feature_paths_env)"

REPO_ROOT=$(get_repo_root)
CURRENT_BRANCH=$(get_current_branch)
HAS_GIT="false"
test_has_git && HAS_GIT="true"
IMPL_PLAN="$REPO_ROOT/specs/$CURRENT_BRANCH/plan.md"
NEW_PLAN="$IMPL_PLAN"

# Agent file paths
CLAUDE_FILE="$REPO_ROOT/CLAUDE.md"
GEMINI_FILE="$REPO_ROOT/GEMINI.md"
COPILOT_FILE="$REPO_ROOT/.github/agents/copilot-instructions.md"
CURSOR_FILE="$REPO_ROOT/.cursor/rules/specify-rules.mdc"
QWEN_FILE="$REPO_ROOT/QWEN.md"
AGENTS_FILE="$REPO_ROOT/AGENTS.md"
WINDSURF_FILE="$REPO_ROOT/.windsurf/rules/specify-rules.md"
KILOCODE_FILE="$REPO_ROOT/.kilocode/rules/specify-rules.md"
AUGGIE_FILE="$REPO_ROOT/.augment/rules/specify-rules.md"
ROO_FILE="$REPO_ROOT/.roo/rules/specify-rules.md"
CODEBUDDY_FILE="$REPO_ROOT/CODEBUDDY.md"
QODER_FILE="$REPO_ROOT/QODER.md"
AMP_FILE="$REPO_ROOT/AGENTS.md"
SHAI_FILE="$REPO_ROOT/SHAI.md"
Q_FILE="$REPO_ROOT/AGENTS.md"
BOB_FILE="$REPO_ROOT/AGENTS.md"

TEMPLATE_FILE="$REPO_ROOT/.specify/templates/agent-file-template.md"

# Parsed plan data
NEW_LANG=""
NEW_FRAMEWORK=""
NEW_DB=""
NEW_PROJECT_TYPE=""

# Helper functions
write_info() {
    echo "INFO: $1"
}

write_success() {
    echo "✓ $1"
}

write_warning() {
    echo "WARNING: $1" >&2
}

write_err() {
    echo "ERROR: $1" >&2
}

validate_environment() {
    if [[ -z "$CURRENT_BRANCH" ]]; then
        write_err 'Unable to determine current feature'
        if [[ "$HAS_GIT" == "true" ]]; then
            write_info "Make sure you're on a feature branch"
        else
            write_info 'Set SPECIFY_FEATURE environment variable or create a feature first'
        fi
        exit 1
    fi
    
    if [[ ! -f "$NEW_PLAN" ]]; then
        write_err "No plan.md found at $NEW_PLAN"
        write_info 'Ensure you are working on a feature with a corresponding spec directory'
        if [[ "$HAS_GIT" != "true" ]]; then
            write_info 'Use: export SPECIFY_FEATURE=your-feature-name or create a new feature first'
        fi
        exit 1
    fi
    
    if [[ ! -f "$TEMPLATE_FILE" ]]; then
        write_err "Template file not found at $TEMPLATE_FILE"
        write_info 'Run specify init to scaffold .specify/templates, or add agent-file-template.md there.'
        exit 1
    fi
}

extract_plan_field() {
    local field_pattern="$1"
    local plan_file="$2"
    
    if [[ ! -f "$plan_file" ]]; then
        return
    fi
    
    grep "^\*\*$field_pattern\*\*:" "$plan_file" | sed -n "s/^\*\*$field_pattern\*\*: \(.*\)$/\1/p" | head -1
}

parse_plan_data() {
    local plan_file="$1"
    
    if [[ ! -f "$plan_file" ]]; then
        write_err "Plan file not found: $plan_file"
        return 1
    fi
    
    write_info "Parsing plan data from $plan_file"
    
    NEW_LANG=$(extract_plan_field 'Language/Version' "$plan_file")
    NEW_FRAMEWORK=$(extract_plan_field 'Primary Dependencies' "$plan_file")
    NEW_DB=$(extract_plan_field 'Storage' "$plan_file")
    NEW_PROJECT_TYPE=$(extract_plan_field 'Project Type' "$plan_file")
    
    [[ -n "$NEW_LANG" ]] && write_info "Found language: $NEW_LANG" || write_warning 'No language information found in plan'
    [[ -n "$NEW_FRAMEWORK" ]] && write_info "Found framework: $NEW_FRAMEWORK"
    [[ -n "$NEW_DB" && "$NEW_DB" != "N/A" ]] && write_info "Found database: $NEW_DB"
    [[ -n "$NEW_PROJECT_TYPE" ]] && write_info "Found project type: $NEW_PROJECT_TYPE"
    
    return 0
}

format_technology_stack() {
    local lang="$1"
    local framework="$2"
    local parts=()
    
    [[ -n "$lang" && "$lang" != "NEEDS CLARIFICATION" ]] && parts+=("$lang")
    [[ -n "$framework" && "$framework" != "NEEDS CLARIFICATION" && "$framework" != "N/A" ]] && parts+=("$framework")
    
    if (( ${#parts[@]} == 0 )); then
        return
    fi
    
    IFS='+' echo "${parts[*]}"
}

update_agent_file() {
    local target_file="$1"
    local agent_name="$2"
    
    if [[ -z "$target_file" || -z "$agent_name" ]]; then
        write_err 'update_agent_file requires target_file and agent_name'
        return 1
    fi
    
    write_info "Updating $agent_name context file: $target_file"
    
    # Create directory if needed
    mkdir -p "$(dirname "$target_file")"
    
    # For now, create a basic file with updated timestamp
    if [[ ! -f "$target_file" ]]; then
        cat > "$target_file" <<EOF
# Agent Context: $agent_name

## Active Technologies
EOF
        [[ -n "$NEW_LANG" ]] && echo "- $NEW_LANG" >> "$target_file"
        [[ -n "$NEW_FRAMEWORK" && "$NEW_FRAMEWORK" != "N/A" ]] && echo "- $NEW_FRAMEWORK" >> "$target_file"
        [[ -n "$NEW_DB" && "$NEW_DB" != "N/A" ]] && echo "- $NEW_DB" >> "$target_file"
        
        cat >> "$target_file" <<EOF

## Recent Changes
EOF
        [[ -n "$NEW_LANG" ]] && echo "- $CURRENT_BRANCH: Added $NEW_LANG" >> "$target_file"
        
        cat >> "$target_file" <<EOF

**Last updated**: $(date +%Y-%m-%d)
EOF
        write_success "Created new $agent_name context file"
    else
        # Update timestamp in existing file
        sed -i '' "s/\*\*Last updated\*\*: .*/\*\*Last updated\*\*: $(date +%Y-%m-%d)/" "$target_file" 2>/dev/null || \
        sed -i "s/\*\*Last updated\*\*: .*/\*\*Last updated\*\*: $(date +%Y-%m-%d)/" "$target_file"
        write_success "Updated existing $agent_name context file"
    fi
    
    return 0
}

update_specific_agent() {
    local agent_type="$1"
    
    case "$agent_type" in
        claude)   update_agent_file "$CLAUDE_FILE" 'Claude Code' ;;
        gemini)   update_agent_file "$GEMINI_FILE" 'Gemini CLI' ;;
        copilot)  update_agent_file "$COPILOT_FILE" 'GitHub Copilot' ;;
        cursor)   update_agent_file "$CURSOR_FILE" 'Cursor IDE' ;;
        qwen)     update_agent_file "$QWEN_FILE" 'Qwen Code' ;;
        opencode) update_agent_file "$AGENTS_FILE" 'opencode' ;;
        codex)    update_agent_file "$AGENTS_FILE" 'Codex CLI' ;;
        windsurf) update_agent_file "$WINDSURF_FILE" 'Windsurf' ;;
        kilocode) update_agent_file "$KILOCODE_FILE" 'Kilo Code' ;;
        auggie)   update_agent_file "$AUGGIE_FILE" 'Auggie CLI' ;;
        roo)      update_agent_file "$ROO_FILE" 'Roo Code' ;;
        codebuddy) update_agent_file "$CODEBUDDY_FILE" 'CodeBuddy CLI' ;;
        qoder)    update_agent_file "$QODER_FILE" 'Qoder CLI' ;;
        amp)      update_agent_file "$AMP_FILE" 'Amp' ;;
        shai)     update_agent_file "$SHAI_FILE" 'SHAI' ;;
        q)        update_agent_file "$Q_FILE" 'Amazon Q Developer CLI' ;;
        bob)      update_agent_file "$BOB_FILE" 'IBM Bob' ;;
        *)
            write_err "Unknown agent type '$agent_type'"
            write_err 'Expected: claude|gemini|copilot|cursor|qwen|opencode|codex|windsurf|kilocode|auggie|roo|codebuddy|amp|shai|q|bob|qoder'
            return 1
            ;;
    esac
}

update_all_existing_agents() {
    local found=false
    local ok=true
    
    for file_var in CLAUDE_FILE GEMINI_FILE COPILOT_FILE CURSOR_FILE QWEN_FILE AGENTS_FILE WINDSURF_FILE KILOCODE_FILE AUGGIE_FILE ROO_FILE CODEBUDDY_FILE QODER_FILE SHAI_FILE Q_FILE BOB_FILE; do
        local file="${!file_var}"
        if [[ -f "$file" ]]; then
            found=true
            local agent_name="${file_var%_FILE}"
            if ! update_agent_file "$file" "$agent_name"; then
                ok=false
            fi
        fi
    done
    
    if [[ "$found" == "false" ]]; then
        write_info 'No existing agent files found, creating default Claude file...'
        if ! update_agent_file "$CLAUDE_FILE" 'Claude Code'; then
            ok=false
        fi
    fi
    
    [[ "$ok" == "true" ]] && return 0 || return 1
}

print_summary() {
    echo ""
    write_info 'Summary of changes:'
    [[ -n "$NEW_LANG" ]] && echo "  - Added language: $NEW_LANG"
    [[ -n "$NEW_FRAMEWORK" ]] && echo "  - Added framework: $NEW_FRAMEWORK"
    [[ -n "$NEW_DB" && "$NEW_DB" != "N/A" ]] && echo "  - Added database: $NEW_DB"
    echo ""
    write_info 'Usage: ./update-agent-context.sh [claude|gemini|copilot|cursor|qwen|opencode|codex|windsurf|kilocode|auggie|roo|codebuddy|amp|shai|q|bob|qoder]'
}

main() {
    validate_environment
    write_info "=== Updating agent context files for feature $CURRENT_BRANCH ==="
    
    if ! parse_plan_data "$NEW_PLAN"; then
        write_err 'Failed to parse plan data'
        exit 1
    fi
    
    local success=true
    
    if [[ -n "$AGENT_TYPE" ]]; then
        write_info "Updating specific agent: $AGENT_TYPE"
        if ! update_specific_agent "$AGENT_TYPE"; then
            success=false
        fi
    else
        write_info 'No agent specified, updating all existing agent files...'
        if ! update_all_existing_agents; then
            success=false
        fi
    fi
    
    print_summary
    
    if [[ "$success" == "true" ]]; then
        write_success 'Agent context update completed successfully'
        exit 0
    else
        write_err 'Agent context update completed with errors'
        exit 1
    fi
}

main
