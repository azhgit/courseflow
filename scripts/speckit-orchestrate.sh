#!/bin/bash

# CourseFlow Speckit Pipeline Orchestrator
# Automatically executes: specify → clarify → plan → tasks → implement
# Usage: ./scripts/speckit-orchestrate.sh "Feature description here"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FEATURE_DESCRIPTION="${1:-}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_TIME=$(date +%s)

# Helper functions
log_stage() {
    echo -e "\n${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_stage "Checking prerequisites..."
    
    if ! command -v copilot &> /dev/null; then
        log_error "Copilot CLI not found. Please install: brew install copilot-cli"
        exit 1
    fi
    
    if [ ! -d "$PROJECT_ROOT/.github/agents" ]; then
        log_error "Speckit agents directory not found"
        exit 1
    fi
    
    log_success "Prerequisites met"
}

# Validate feature description
validate_input() {
    if [ -z "$FEATURE_DESCRIPTION" ]; then
        log_error "Feature description required"
        echo -e "\n${YELLOW}Usage:${NC}"
        echo "  ./scripts/speckit-orchestrate.sh \"Feature description here\""
        echo ""
        echo "${YELLOW}Example:${NC}"
        echo "  ./scripts/speckit-orchestrate.sh \"Document ingestion with duplicate detection\""
        exit 1
    fi
    
    log_stage "Feature Description"
    echo "  📝 $FEATURE_DESCRIPTION"
}

# Execute each stage
execute_specify() {
    log_stage "[Stage 1/5] SPECIFY"
    log_warning "Please use: /speckit.specify with your feature description"
    log_warning "Or invoke via Copilot agent: /speckit.specify $FEATURE_DESCRIPTION"
    
    # Note: This is a placeholder - actual execution requires Copilot CLI agent system
    echo "  → Waiting for specification to be created..."
    echo "  → Specs should be saved to: specs/{feature-slug}/spec.md"
}

execute_clarify() {
    log_stage "[Stage 2/5] CLARIFY"
    log_warning "Please use: /speckit.clarify"
    log_warning "Answer the interactive questions (Q1-Q5) to resolve ambiguities"
    
    echo "  → Waiting for clarification to complete..."
    echo "  → Results saved to memory and specs/{feature-slug}/checklist.md"
}

execute_plan() {
    log_stage "[Stage 3/5] PLAN"
    log_warning "Please use: /speckit.plan"
    
    echo "  → Waiting for plan generation..."
    echo "  → Plan saved to: specs/{feature-slug}/plan.md"
}

execute_tasks() {
    log_stage "[Stage 4/5] TASKS"
    log_warning "Please use: /speckit.tasks"
    
    echo "  → Waiting for task list generation..."
    echo "  → Tasks saved to: specs/{feature-slug}/tasks.md"
}

execute_implement() {
    log_stage "[Stage 5/5] IMPLEMENT"
    log_warning "Please use: /speckit.implement"
    log_warning "This may take 20-30+ minutes depending on task count"
    
    echo "  → Waiting for implementation to complete..."
    echo "  → Check stdout for progress on each task"
}

print_summary() {
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))
    
    echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Speckit Pipeline Orchestration       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "📊 Pipeline Status"
    echo "  Feature: $FEATURE_DESCRIPTION"
    echo "  Duration: ${MINUTES}m ${SECONDS}s"
    echo ""
    echo "📁 Expected Artifacts"
    echo "  ├─ specs/{feature-slug}/spec.md"
    echo "  ├─ specs/{feature-slug}/plan.md"
    echo "  ├─ specs/{feature-slug}/tasks.md"
    echo "  ├─ specs/{feature-slug}/quickstart.md"
    echo "  └─ src/courseflow/... (implementation files)"
    echo ""
    echo "🚀 Next Steps"
    echo "  1. Review generated artifacts"
    echo "  2. Run: git add . && git commit -m 'feat: complete feature'"
    echo "  3. Run: git push origin"
    echo ""
}

print_interactive_guide() {
    echo -e "\n${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Interactive Speckit Pipeline Guide     ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo "📋 How to Execute Full Pipeline Manually"
    echo ""
    echo "Step 1: START SPECIFY STAGE"
    echo "  Command: /speckit.specify $FEATURE_DESCRIPTION"
    echo ""
    echo "Step 2: START CLARIFY STAGE"
    echo "  Command: /speckit.clarify"
    echo "  Action: Answer 5 interactive questions"
    echo ""
    echo "Step 3: START PLAN STAGE"
    echo "  Command: /speckit.plan"
    echo ""
    echo "Step 4: START TASKS STAGE"
    echo "  Command: /speckit.tasks"
    echo ""
    echo "Step 5: START IMPLEMENT STAGE"
    echo "  Command: /speckit.implement"
    echo "  Action: Review and confirm task execution"
    echo ""
    echo "⏱️  Total estimated time: 45-60 minutes"
    echo ""
}

print_orchestrate_option() {
    echo -e "\n${YELLOW}💡 Full Automation Option${NC}"
    echo ""
    echo "For complete hands-off execution, try:"
    echo "  ${BLUE}/speckit.orchestrate $FEATURE_DESCRIPTION${NC}"
    echo ""
    echo "This will:"
    echo "  1. Execute all 5 stages automatically"
    echo "  2. Handle all stage transitions"
    echo "  3. Prompt for user input only when necessary"
    echo "  4. Provide progress updates"
    echo ""
}

# Main execution
main() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Speckit Pipeline Orchestrator v0.1    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    
    check_prerequisites
    validate_input
    
    echo ""
    log_stage "Pipeline Configuration"
    echo "  Feature: $FEATURE_DESCRIPTION"
    echo "  Stages: 5 (specify → clarify → plan → tasks → implement)"
    echo "  Estimated Duration: 45-60 minutes"
    echo ""
    
    # Display options
    print_interactive_guide
    print_orchestrate_option
    
    # Show what would happen
    echo -e "${YELLOW}📝 To execute the pipeline:${NC}"
    echo ""
    echo "Option A: Use Speckit.orchestrate agent (recommended)"
    echo "  ${BLUE}copilot /speckit.orchestrate ${FEATURE_DESCRIPTION}${NC}"
    echo ""
    echo "Option B: Manual stage-by-stage execution"
    echo "  Step 1: ${BLUE}copilot /speckit.specify ${FEATURE_DESCRIPTION}${NC}"
    echo "  Step 2: ${BLUE}copilot /speckit.clarify${NC}"
    echo "  Step 3: ${BLUE}copilot /speckit.plan${NC}"
    echo "  Step 4: ${BLUE}copilot /speckit.tasks${NC}"
    echo "  Step 5: ${BLUE}copilot /speckit.implement${NC}"
    echo ""
    
    print_summary
}

# Run main function
main "$@"
