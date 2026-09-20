#!/usr/bin/env bash
#
# docker-start.sh — The Textile Care Docker Launcher
#
# Usage:
#   ./scripts/docker-start.sh                        # Interactive menu
#   ./scripts/docker-start.sh all                    # All web + backend
#   ./scripts/docker-start.sh backend                # Backend + infra only
#   ./scripts/docker-start.sh marketplace-web        # One service
#   ./scripts/docker-start.sh all mobile-dev         # Web + mobile dev servers
#   ./scripts/docker-start.sh mobile-build           # Build all mobile APKs
#   ./scripts/docker-start.sh --down                 # Stop & remove containers
#   ./scripts/docker-start.sh --logs marketplace-web # Tail logs for a service
#   ./scripts/docker-start.sh --build all            # Force rebuild images
#   ./scripts/docker-start.sh --help
#

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}==>${RESET} $*"; }
success() { echo -e "${GREEN}✔${RESET}  $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET}  $*"; }
error()   { echo -e "${RED}✖${RESET}  $*" >&2; exit 1; }
bold()    { echo -e "${BOLD}$*${RESET}"; }

# ── Service catalogue ──────────────────────────────────────────────────────────
# Each service maps to: compose-service-name | profile (or "default")
declare -A SVC_PROFILE=(
  [admin-web]="default"
  [marketplace-web]="default"
  [seller-web]="default"
  [backend]="default"
  [postgres]="default"
  [redis]="default"
  [marketplace-mobile-dev]="mobile-dev"
  [seller-mobile-dev]="mobile-dev"
  [driver-mobile-dev]="mobile-dev"
  [marketplace-mobile-apk]="mobile-build-apk"
  [seller-mobile-apk]="mobile-build-apk"
  [driver-mobile-apk]="mobile-build-apk"
  [marketplace-mobile-aab]="mobile-build-aab"
  [seller-mobile-aab]="mobile-build-aab"
  [driver-mobile-aab]="mobile-build-aab"
)

# Groups
ALL_WEB=(admin-web marketplace-web seller-web)
ALL_INFRA=(postgres redis)
ALL_DEFAULT=(admin-web marketplace-web seller-web backend postgres redis)
ALL_MOBILE_DEV=(marketplace-mobile-dev seller-mobile-dev driver-mobile-dev)
ALL_MOBILE_APK=(marketplace-mobile-apk seller-mobile-apk driver-mobile-apk)
ALL_MOBILE_AAB=(marketplace-mobile-aab seller-mobile-aab driver-mobile-aab)

# ── Menu ───────────────────────────────────────────────────────────────────────
show_menu() {
  echo ""
  bold "╔══════════════════════════════════════════════════════╗"
  bold "║       THE TEXTILE CARE — Docker Launcher             ║"
  bold "╚══════════════════════════════════════════════════════╝"
  echo ""
  bold "Individual Services:"
  echo "  1)  admin-web              Admin portal            → :3000"
  echo "  2)  marketplace-web        Customer marketplace    → :3001"
  echo "  3)  seller-web             Seller portal           → :3002"
  echo "  4)  backend                FastAPI backend         → :8000"
  echo "  5)  postgres               PostgreSQL              → :5432"
  echo "  6)  redis                  Redis cache             → :6379"
  echo ""
  bold "Mobile Dev Servers (Expo Metro — connect via Expo Go):"
  echo "  7)  marketplace-mobile-dev  Customer app Metro     → :8081"
  echo "  8)  seller-mobile-dev       Seller app Metro       → :8082"
  echo "  9)  driver-mobile-dev       Driver app Metro       → :8083"
  echo ""
  bold "Mobile Android APK Builds (outputs .apk for testing):"
  echo " 10)  marketplace-mobile-apk"
  echo " 11)  seller-mobile-apk"
  echo " 12)  driver-mobile-apk"
  echo ""
  bold "Mobile Android AAB Builds (outputs .aab for Play Store):"
  echo " 13)  marketplace-mobile-aab"
  echo " 14)  seller-mobile-aab"
  echo " 15)  driver-mobile-aab"
  echo ""
  bold "Groups:"
  echo " 16)  all-web         Web apps + backend + infra"
  echo " 17)  mobile-dev      All mobile dev servers"
  echo " 18)  mobile-apk      All mobile APK builds"
  echo " 19)  mobile-aab      All mobile AAB builds"
  echo " 20)  all             Everything (web + dev servers)"
  echo ""
  echo "  Enter one or more numbers/names: e.g. '1 4' or 'all mobile-dev'"
  echo ""
}

# ── Token resolver ─────────────────────────────────────────────────────────────
RESOLVED_SVCS=()

resolve_token() {
  local t="$1"
  case "$t" in
    1|admin|admin-web)                RESOLVED_SVCS+=(admin-web) ;;
    2|marketplace|marketplace-web)    RESOLVED_SVCS+=(marketplace-web) ;;
    3|seller|seller-web)              RESOLVED_SVCS+=(seller-web) ;;
    4|backend|api)                    RESOLVED_SVCS+=(backend) ;;
    5|postgres|db)                    RESOLVED_SVCS+=(postgres) ;;
    6|redis|cache)                    RESOLVED_SVCS+=(redis) ;;
    7|marketplace-mobile-dev)         RESOLVED_SVCS+=(marketplace-mobile-dev) ;;
    8|seller-mobile-dev)              RESOLVED_SVCS+=(seller-mobile-dev) ;;
    9|driver-mobile-dev)              RESOLVED_SVCS+=(driver-mobile-dev) ;;
    10|marketplace-mobile-apk)        RESOLVED_SVCS+=(marketplace-mobile-apk) ;;
    11|seller-mobile-apk)             RESOLVED_SVCS+=(seller-mobile-apk) ;;
    12|driver-mobile-apk)             RESOLVED_SVCS+=(driver-mobile-apk) ;;
    13|marketplace-mobile-aab)        RESOLVED_SVCS+=(marketplace-mobile-aab) ;;
    14|seller-mobile-aab)             RESOLVED_SVCS+=(seller-mobile-aab) ;;
    15|driver-mobile-aab)             RESOLVED_SVCS+=(driver-mobile-aab) ;;
    16|web|all-web)                   RESOLVED_SVCS+=("${ALL_DEFAULT[@]}") ;;
    17|mobile-dev|all-mobile-dev)     RESOLVED_SVCS+=("${ALL_MOBILE_DEV[@]}") ;;
    18|mobile-apk|all-mobile-apk)     RESOLVED_SVCS+=("${ALL_MOBILE_APK[@]}") ;;
    19|mobile-aab|all-mobile-aab)     RESOLVED_SVCS+=("${ALL_MOBILE_AAB[@]}") ;;
    20|all)
      RESOLVED_SVCS+=("${ALL_DEFAULT[@]}" "${ALL_MOBILE_DEV[@]}")
      ;;
    *)
      error "Unknown service or group: '$t'\nRun with --help to see available options."
      ;;
  esac
}

dedupe() {
  local -A seen; local unique=()
  for s in "${RESOLVED_SVCS[@]}"; do
    [[ -z "${seen[$s]}" ]] && seen[$s]=1 && unique+=("$s")
  done
  RESOLVED_SVCS=("${unique[@]}")
}

# ── Flags ──────────────────────────────────────────────────────────────────────
DO_BUILD=false
DO_DOWN=false
DO_LOGS=""
DO_DETACH=false
DO_DRY_RUN=false
CLI_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_menu
      echo "Flags:"
      echo "  --build      Force rebuild Docker images before starting"
      echo "  --down       Stop and remove all containers"
      echo "  --detach/-d  Start in detached (background) mode"
      echo "  --logs <svc> Tail logs for a specific service"
      echo "  --dry-run    Print the docker compose command without running it"
      exit 0 ;;
    --build)    DO_BUILD=true;    shift ;;
    --down)     DO_DOWN=true;     shift ;;
    -d|--detach) DO_DETACH=true;  shift ;;
    --dry-run)  DO_DRY_RUN=true;  shift ;;
    --logs)     DO_LOGS="$2";     shift 2 ;;
    *)          CLI_ARGS+=("$1"); shift ;;
  esac
done

# ── --down shortcut ────────────────────────────────────────────────────────────
if [ "$DO_DOWN" = true ]; then
  info "Stopping and removing all TTC containers..."
  docker compose \
    --profile mobile-dev \
    --profile mobile-build \
    down --remove-orphans
  success "All containers stopped."
  exit 0
fi

# ── --logs shortcut ────────────────────────────────────────────────────────────
if [ -n "$DO_LOGS" ]; then
  info "Tailing logs for: $DO_LOGS"
  docker compose logs -f "$DO_LOGS"
  exit 0
fi

# ── Check prerequisites ────────────────────────────────────────────────────────
command -v docker >/dev/null 2>&1 || error "Docker is not installed or not in PATH."
docker info >/dev/null 2>&1      || error "Docker daemon is not running."

if [ ! -f "$REPO_ROOT/.env" ]; then
  warn ".env not found — copying from .env.example"
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  warn "Review and edit .env before running in production."
fi

# ── Resolve services ────────────────────────────────────────────────────────────
if [ ${#CLI_ARGS[@]} -gt 0 ]; then
  for arg in "${CLI_ARGS[@]}"; do
    for token in ${arg//,/ }; do resolve_token "$token"; done
  done
else
  show_menu
  local_sel=""
  if [ -t 0 ]; then
    printf "Select service(s) to start: "
    read -r local_sel || true
  else
    read -r local_sel || true
  fi
  local_sel="$(echo "$local_sel" | xargs 2>/dev/null || echo "$local_sel")"
  [ -z "$local_sel" ] && { echo "Nothing selected. Exiting."; exit 0; }
  for token in ${local_sel//,/ }; do resolve_token "$token"; done
fi

dedupe

[ ${#RESOLVED_SVCS[@]} -eq 0 ] && { warn "No valid services selected."; exit 0; }

# ── Collect required profiles ──────────────────────────────────────────────────
PROFILES=()
NEEDS_MOBILE_DEV=false
NEEDS_MOBILE_APK=false
NEEDS_MOBILE_AAB=false

for svc in "${RESOLVED_SVCS[@]}"; do
  p="${SVC_PROFILE[$svc]:-default}"
  case "$p" in
    mobile-dev)       NEEDS_MOBILE_DEV=true ;;
    mobile-build-apk) NEEDS_MOBILE_APK=true ;;
    mobile-build-aab) NEEDS_MOBILE_AAB=true ;;
  esac
done

PROFILE_FLAGS=()
[ "$NEEDS_MOBILE_DEV" = true ] && PROFILE_FLAGS+=(--profile mobile-dev)
[ "$NEEDS_MOBILE_APK" = true ] && PROFILE_FLAGS+=(--profile mobile-build-apk)
[ "$NEEDS_MOBILE_AAB" = true ] && PROFILE_FLAGS+=(--profile mobile-build-aab)

# ── Detect build-only services (mobile APK/AAB) ────────────────────────────────
BUILD_ONLY_SVCS=()
RUN_SVCS=()
for svc in "${RESOLVED_SVCS[@]}"; do
  p="${SVC_PROFILE[$svc]:-default}"
  if [[ "$p" == mobile-build-* ]]; then
    BUILD_ONLY_SVCS+=("$svc")
  else
    RUN_SVCS+=("$svc")
  fi
done

# ── Build the compose command ───────────────────────────────────────────────────
BUILD_FLAG=()
[ "$DO_BUILD" = true ] && BUILD_FLAG=(--build)

DETACH_FLAG=()
[ "$DO_DETACH" = true ] && DETACH_FLAG=(-d)

echo ""
bold "Services selected: ${RESOLVED_SVCS[*]}"
echo ""

# ── Dry-run ────────────────────────────────────────────────────────────────────
if [ "$DO_DRY_RUN" = true ]; then
  info "[DRY-RUN] Would run:"
  if [ ${#RUN_SVCS[@]} -gt 0 ]; then
    echo "  docker compose ${PROFILE_FLAGS[*]} up ${BUILD_FLAG[*]} ${DETACH_FLAG[*]} ${RUN_SVCS[*]}"
  fi
  for svc in "${BUILD_ONLY_SVCS[@]}"; do
    echo "  docker compose ${PROFILE_FLAGS[*]} run --rm $svc"
    echo "  # APK output → ./dist/mobile/"
  done
  exit 0
fi

# ── Run long-running services ──────────────────────────────────────────────────
if [ ${#RUN_SVCS[@]} -gt 0 ]; then
  info "Starting: ${RUN_SVCS[*]}"
  docker compose "${PROFILE_FLAGS[@]}" up "${BUILD_FLAG[@]}" "${DETACH_FLAG[@]}" "${RUN_SVCS[@]}"
fi

# ── Run build-only services (mobile APK builds) ────────────────────────────────
if [ ${#BUILD_ONLY_SVCS[@]} -gt 0 ]; then
  mkdir -p "$REPO_ROOT/dist/mobile"
  for svc in "${BUILD_ONLY_SVCS[@]}"; do
    info "Building APK: $svc (this may take 10-20 min first run)..."
    docker compose "${PROFILE_FLAGS[@]}" run --rm "$svc"
    success "$svc build complete → ./dist/mobile/"
  done
fi

echo ""
success "Done."
