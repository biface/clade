#!/usr/bin/env bash
# =============================================================================
# .tox-config/scripts/coverage.sh — Hierarchy project
# =============================================================================
# Génération du rapport de couverture.
# Lit .tox-config/coverage-version.txt pour l'environnement cible.
#
# Usage:
#   ./.tox-config/scripts/coverage.sh [coverage_version_file]
#
# Codes de sortie:
#   0: Rapport généré avec succès
#   1: Échec de génération
# =============================================================================

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
readonly COVERAGE_VERSION_FILE="${1:-${PROJECT_ROOT}/.tox-config/coverage-version.txt}"
readonly DEFAULT_COVERAGE_ENV="py312-dj52"

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

get_coverage_env() {
    local coverage_env="${DEFAULT_COVERAGE_ENV}"

    if [[ ! -f "${COVERAGE_VERSION_FILE}" ]]; then
        log_warning "File not found: ${COVERAGE_VERSION_FILE}"
        log_info "Using default: ${DEFAULT_COVERAGE_ENV}"
        echo "${coverage_env}"
        return 0
    fi

    while IFS= read -r line || [[ -n "${line}" ]]; do
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "${line}" ]] && continue
        [[ "${line}" =~ ^# ]] && continue
        coverage_env="${line}"
        break
    done < "${COVERAGE_VERSION_FILE}"

    echo "${coverage_env}"
}

generate_coverage() {
    cd "${PROJECT_ROOT}"

    local coverage_env
    coverage_env=$(get_coverage_env)

    log_info "Coverage environment: ${coverage_env}"
    log_section "Generating coverage report"

    tox -e coverage || { log_error "Coverage generation failed"; return 1; }

    log_success "Coverage report generated"
    echo ""
    log_info "Reports:"
    [[ -f "coverage/coverage.xml" ]]    && log_info "  XML:  coverage/coverage.xml"
    [[ -d "coverage/coverage_html" ]]   && log_info "  HTML: coverage/coverage_html/index.html"
}

main() {
    log_info "Starting coverage report generation"
    log_info "Working directory: ${PROJECT_ROOT}"
    generate_coverage && log_success "Completed successfully" && exit 0
    log_error "Coverage generation failed"
    exit 1
}

main "$@"
