#!/usr/bin/env bash
#
# start.sh - The Textile Care Monorepo Development Server Launcher
#
# Usage:
#   ./start.sh [options] [app1 app2 ...]
#
# Examples:
#   ./start.sh                      # Launch interactive selection menu
#   ./start.sh admin-web            # Start only admin-web
#   ./start.sh backend              # Start only backend
#   ./start.sh admin-web backend    # Start admin-web and backend concurrently
#   ./start.sh all                  # Start all core applications
#   ./start.sh web                  # Start all web applications
#   ./start.sh --help               # Show help and usage information
#

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

cd "$REPO_ROOT"

# Available application mappings
# Canonical names: admin-web, marketplace-web, seller-web, backend, driver-mobile, marketplace-mobile, seller-mobile
ALL_WEB_APPS=("admin-web" "marketplace-web" "seller-web")
ALL_MOBILE_APPS=("driver-mobile" "marketplace-mobile" "seller-mobile")
ALL_CORE_APPS=("admin-web" "marketplace-web" "seller-web" "backend")
ALL_APPS=("admin-web" "marketplace-web" "seller-web" "backend" "driver-mobile" "marketplace-mobile" "seller-mobile")

# Global PIDs array for lifecycle management
PIDS=()
CLEANING_UP=false

# Cleanup handler for graceful shutdown
cleanup() {
  # Avoid recursive calls
  if [ "$CLEANING_UP" = true ]; then
    return
  fi
  CLEANING_UP=true

  # Reset signals to default
  trap - SIGINT SIGTERM EXIT

  if [ ${#PIDS[@]} -eq 0 ]; then
    return
  fi

  echo ""
  echo "==> Shutting down development servers..."

  # Send SIGTERM to all child processes and process trees
  for pid in "${PIDS[@]}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done

  # Also signal any children of this shell
  pkill -TERM -P $$ 2>/dev/null || true

  # Brief grace period for clean shutdown
  sleep 0.5

  # Force kill any lingering processes
  for pid in "${PIDS[@]}"; do
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      pkill -KILL -P "$pid" 2>/dev/null || true
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done
  pkill -KILL -P $$ 2>/dev/null || true

  wait 2>/dev/null || true
  echo "==> All development servers stopped."
}

# Trap signals for lifecycle management
trap cleanup SIGINT SIGTERM EXIT

# Help message
show_help() {
  cat <<'EOF'
The Textile Care - Development Server Launcher (start.sh)

Usage:
  ./start.sh [options] [app...]

Options:
  -h, --help        Show this help message and exit
  -l, --list        List all available applications and exit
  --dry-run         Print the commands that would be executed without starting them
  --pnpm            Use pnpm directly instead of turbo for web apps

Applications:
  1) admin-web           Next.js Admin Portal (web)
  2) marketplace-web     Next.js Marketplace (web)
  3) seller-web          Next.js Seller Portal (web)
  4) backend             FastAPI Python Backend (api)
  5) driver-mobile       Expo Driver Mobile App (mobile)
  6) marketplace-mobile  Expo Marketplace Mobile App (mobile)
  7) seller-mobile       Expo Seller Mobile App (mobile)

Group Aliases:
  web, all-web           Start all 3 web apps (admin-web, marketplace-web, seller-web)
  mobile, all-mobile     Start all 3 mobile apps
  all                    Start all core services (admin-web, marketplace-web, seller-web, backend)

Examples:
  ./start.sh                      # Launch interactive menu
  ./start.sh admin-web            # Start only admin-web
  ./start.sh backend              # Start only backend
  ./start.sh admin-web backend    # Start admin-web and backend concurrently
  ./start.sh 1 4                  # Start by number: admin-web and backend
  ./start.sh all                  # Start all core applications
EOF
}

# Display interactive menu / application overview
show_menu() {
  cat <<'EOF'
=====================================================
    The Textile Care - Development Server Launcher   
=====================================================

Available Applications:
  1) admin-web           - Next.js Admin Portal
  2) marketplace-web     - Next.js Marketplace
  3) seller-web          - Next.js Seller Portal
  4) backend             - FastAPI Python Backend
  5) driver-mobile       - Expo Driver Mobile App
  6) marketplace-mobile  - Expo Marketplace Mobile App
  7) seller-mobile       - Expo Seller Mobile App

Application Groups:
  8) all-web             - All Web Applications (1-3)
  9) all-mobile          - All Mobile Applications (5-7)
 10) all                 - All Core Applications (1-4)

How to select:
  - Enter one or more numbers or app names separated by spaces
    (e.g., '1 4', 'admin-web backend', or 'all')
  - Or run directly with arguments: ./start.sh admin-web backend

EOF
}

# Resolve input tokens to canonical application names
# Appends resolved names to RESOLVED_APPS array
RESOLVED_APPS=()

resolve_token() {
  local token="$1"
  case "$token" in
    1|admin|admin-web|@ttc/admin-web)
      RESOLVED_APPS+=("admin-web")
      ;;
    2|marketplace|marketplace-web|market-web|@ttc/marketplace-web)
      RESOLVED_APPS+=("marketplace-web")
      ;;
    3|seller|seller-web|@ttc/seller-web)
      RESOLVED_APPS+=("seller-web")
      ;;
    4|backend|api|server)
      RESOLVED_APPS+=("backend")
      ;;
    5|driver|driver-mobile|@ttc/driver-mobile)
      RESOLVED_APPS+=("driver-mobile")
      ;;
    6|marketplace-mobile|market-mobile|@ttc/marketplace-mobile)
      RESOLVED_APPS+=("marketplace-mobile")
      ;;
    7|seller-mobile|@ttc/seller-mobile)
      RESOLVED_APPS+=("seller-mobile")
      ;;
    8|web|all-web)
      RESOLVED_APPS+=("${ALL_WEB_APPS[@]}")
      ;;
    9|mobile|all-mobile)
      RESOLVED_APPS+=("${ALL_MOBILE_APPS[@]}")
      ;;
    10|all)
      RESOLVED_APPS+=("${ALL_CORE_APPS[@]}")
      ;;
    *)
      echo "Error: Unknown application or option: '$token'" >&2
      echo "Run './start.sh --help' or './start.sh --list' to view available applications." >&2
      exit 1
      ;;
  esac
}

# Deduplicate an array while preserving order
deduplicate_apps() {
  local -A seen
  local unique=()
  for item in "${RESOLVED_APPS[@]}"; do
    if [[ -z "${seen[$item]}" ]]; then
      seen[$item]=1
      unique+=("$item")
    fi
  done
  RESOLVED_APPS=("${unique[@]}")
}

# Parse command-line flags
DRY_RUN=false
USE_PNPM_DIRECT=false
CLI_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    -l|--list)
      echo "Available applications: ${ALL_APPS[*]}"
      echo "Available groups: all-web, all-mobile, all"
      exit 0
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --pnpm)
      USE_PNPM_DIRECT=true
      shift
      ;;
    --turbo)
      USE_PNPM_DIRECT=false
      shift
      ;;
    *)
      CLI_ARGS+=("$1")
      shift
      ;;
  esac
done

# If arguments were provided via CLI
if [ ${#CLI_ARGS[@]} -gt 0 ]; then
  for arg in "${CLI_ARGS[@]}"; do
    # Replace any commas with spaces for easy parsing
    normalized="${arg//,/ }"
    for token in $normalized; do
      resolve_token "$token"
    done
  done
else
  # No CLI arguments provided: present the menu / interactive selection
  show_menu

  user_selection=""
  if [ -t 0 ]; then
    # Interactive terminal
    printf "Select application(s) to start: "
    read -r user_selection || true
  else
    # Non-interactive / piped input
    if read -r user_selection; then
      : # Successfully read from pipe
    else
      # Reached EOF with no input (e.g. ./start.sh < /dev/null)
      echo "Tip: Run './start.sh <app-name>' or run in an interactive terminal to select."
      exit 0
    fi
  fi

  # Trim leading/trailing whitespace
  user_selection="$(echo "$user_selection" | xargs 2>/dev/null || echo "$user_selection")"

  if [ -z "$user_selection" ]; then
    echo "No application selected. Exiting."
    exit 0
  fi

  # Replace commas with spaces
  normalized="${user_selection//,/ }"
  for token in $normalized; do
    resolve_token "$token"
  done
fi

# Deduplicate selected applications
deduplicate_apps

if [ ${#RESOLVED_APPS[@]} -eq 0 ]; then
  echo "No valid applications selected. Exiting."
  exit 0
fi

# Categorize selected applications
SELECTED_WEB=()
SELECTED_MOBILE=()
BACKEND_SELECTED=false

for app in "${RESOLVED_APPS[@]}"; do
  case "$app" in
    admin-web|marketplace-web|seller-web)
      SELECTED_WEB+=("$app")
      ;;
    driver-mobile|marketplace-mobile|seller-mobile)
      SELECTED_MOBILE+=("$app")
      ;;
    backend)
      BACKEND_SELECTED=true
      ;;
  esac
done


get_port_for_app() {
  case "$1" in
    admin-web) echo 3000 ;;
    marketplace-web) echo 3001 ;;
    seller-web) echo 3002 ;;
    backend) echo 8000 ;;
    driver-mobile|marketplace-mobile|seller-mobile) echo 8081 ;;
    *) echo "" ;;
  esac
}

kill_port() {
  local port=$1
  if [ -n "$port" ]; then
    local pid=$(lsof -ti tcp:$port 2>/dev/null)
    if [ -n "$pid" ]; then
      echo "==> Port $port is busy. Killing process $pid..."
      kill -9 $pid 2>/dev/null || true
      sleep 1
    fi
  fi
}

for app in "${RESOLVED_APPS[@]}"; do
  port=$(get_port_for_app "$app")
  if [ -n "$port" ]; then
    kill_port "$port"
  fi
done

echo "==> Preparing to start: ${RESOLVED_APPS[*]}"

# Find uvicorn command for backend if selected
UVICORN_BIN=""
if [ "$BACKEND_SELECTED" = true ]; then
  if [ -x "$REPO_ROOT/backend/.venv/bin/uvicorn" ]; then
    UVICORN_BIN="$REPO_ROOT/backend/.venv/bin/uvicorn"
  elif [ -x "$REPO_ROOT/.venv/bin/uvicorn" ]; then
    UVICORN_BIN="$REPO_ROOT/.venv/bin/uvicorn"
  elif command -v uvicorn >/dev/null 2>&1; then
    UVICORN_BIN="uvicorn"
  elif command -v python3 >/dev/null 2>&1; then
    UVICORN_BIN="python3 -m uvicorn"
  else
    echo "Error: uvicorn/python3 could not be found to start the backend." >&2
    exit 1
  fi
fi

# Execute or dry-run applications
if [ "$DRY_RUN" = true ]; then
  echo "==> [DRY-RUN MODE] Commands to execute:"
  if [ ${#SELECTED_WEB[@]} -gt 0 ]; then
    if [ "$USE_PNPM_DIRECT" = true ]; then
      for web_app in "${SELECTED_WEB[@]}"; do
        echo "  - pnpm --filter @ttc/$web_app dev"
      done
    else
      turbo_filters=()
      for web_app in "${SELECTED_WEB[@]}"; do
        turbo_filters+=("--filter=@ttc/$web_app")
      done
      echo "  - pnpm turbo run dev ${turbo_filters[*]}"
    fi
  fi

  if [ "$BACKEND_SELECTED" = true ]; then
    echo "  - (cd backend && $UVICORN_BIN app.main:app --reload --host 0.0.0.0 --port ${BACKEND_PORT:-8000})"
  fi

  for mobile_app in "${SELECTED_MOBILE[@]}"; do
    echo "  - pnpm --filter @ttc/$mobile_app start"
  done
  exit 0
fi

# Start Web applications
if [ ${#SELECTED_WEB[@]} -gt 0 ]; then
  if [ "$USE_PNPM_DIRECT" = true ]; then
    for web_app in "${SELECTED_WEB[@]}"; do
      echo "==> Starting web application: $web_app via pnpm..."
      pnpm --filter "@ttc/$web_app" dev &
      PIDS+=("$!")
    done
  else
    turbo_filters=()
    for web_app in "${SELECTED_WEB[@]}"; do
      turbo_filters+=("--filter=@ttc/$web_app")
    done
    echo "==> Starting web application(s): ${SELECTED_WEB[*]} via turbo..."
    pnpm turbo run dev "${turbo_filters[@]}" &
    PIDS+=("$!")
  fi
fi

# Start Backend application
if [ "$BACKEND_SELECTED" = true ]; then
  echo "==> Starting backend application on port ${BACKEND_PORT:-8000}..."
  (
    export PYTHONUNBUFFERED=1
    cd "$REPO_ROOT/backend"
    exec "$UVICORN_BIN" app.main:app --reload --host 0.0.0.0 --port "${BACKEND_PORT:-8000}" 2>&1 | while IFS= read -r line; do
      printf "[backend] %s\n" "$line"
    done
  ) &
  PIDS+=("$!")
fi

# Start Mobile applications
for mobile_app in "${SELECTED_MOBILE[@]}"; do
  echo "==> Starting mobile application: $mobile_app via pnpm..."
  (
    cd "$REPO_ROOT/apps/$mobile_app"
    exec pnpm start 2>&1 | while IFS= read -r line; do
      printf "[%s] %s\n" "$mobile_app" "$line"
    done
  ) &
  PIDS+=("$!")
done

echo ""
echo "==> Successfully launched ${#RESOLVED_APPS[@]} service(s) concurrently."
echo "==> Press Ctrl+C to terminate all services."
echo ""

# Wait for background processes
wait
