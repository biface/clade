#!/usr/bin/env bash
# =============================================================================
# .tox-config/scripts/test.sh — Hierarchy project
# =============================================================================
# Exécution séquentielle des tests multi-environnements.
# Lit .tox-config/versions.txt pour déterminer les environnements à tester.
#
# Usage:
#   ./.tox-config/scripts/test.sh [versions_file]
#
# Codes de sortie:
#   0: Tous les tests ont réussi
#   1: Au moins un test a échoué
# =============================================================================

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly VERSIONS_FILE="${1:-${PROJECT_ROOT}/.tox-config/versions.txt}"

log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_section() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}$*${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
}

run_tests() {
    cd "${PROJECT_ROOT}"

    if [[ ! -f "${VERSIONS_FILE}" ]]; then
        log_warning "File not found: ${VERSIONS_FILE}"
        log_info "Using default: py312-dj52"
        tox -e "py312-dj52" || { log_error "Tests failed for py312-dj52"; return 1; }
        return 0
    fi

    log_info "Reading versions from: ${VERSIONS_FILE}"

    local versions=()
    while IFS= read -r line || [[ -n "${line}" ]]; do
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "${line}" ]] && continue
        [[ "${line}" =~ ^# ]] && continue
        versions+=("${line}")
    done < "${VERSIONS_FILE}"

    if [[ ${#versions[@]} -eq 0 ]]; then
        log_warning "No versions found — using default: py312-dj52"
        versions=(py312-dj52)
    fi

    log_info "Test environments: ${versions[*]}"

    local total=${#versions[@]}
    local current=0

    for env in "${versions[@]}"; do
        ((current++))
        log_section "Running ${env} (${current}/${total})"
        tox -e "${env}" || { log_error "Failed: ${env} (${current}/${total})"; return 1; }
        log_success "Passed: ${env} (${current}/${total})"
    done

    echo ""
    log_success "All tests passed! (${total}/${total})"
}

main() {
    log_info "Starting sequential test execution"
    log_info "Working directory: ${PROJECT_ROOT}"
    run_tests && log_success "Completed successfully" && exit 0
    log_error "Test execution failed"
    exit 1
}

main "$@"
