#!/bin/bash
set -e

REPO_URL="https://github.com/hellojuantu/zombie_crisis.git"
REMOTE_VERSION_URL="https://raw.githubusercontent.com/hellojuantu/zombie_crisis/refs/heads/main/VERSION"
INSTALL_DIR="${ZOMBIE_CRISIS_INSTALL_DIR:-$HOME/zombie_crisis}"
STATE_DIR="${ZOMBIE_CRISIS_STATE_DIR:-$HOME/.zombie_crisis}"
BIN_DIR="$STATE_DIR/bin"
CONTROL_BIN="$BIN_DIR/zombie-crisis"
LOG_DIR="$STATE_DIR/logs"
INSTALL_LOG="$LOG_DIR/install.log"
SERVER_LOG="$LOG_DIR/server.log"
PID_FILE="$STATE_DIR/server.pid"
STATE_VERSION_FILE="$STATE_DIR/version"
URL="http://localhost:8080/"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[僵尸危机]${NC} $1"; }
warn() { echo -e "${YELLOW}[警告]${NC} $1"; }
error() {
  echo -e "${RED}[错误]${NC} $1" >&2
  exit 1
}

ensure_state_dirs() {
  mkdir -p "$BIN_DIR" "$LOG_DIR"
}

run_quiet() {
  local label="$1"
  shift
  ensure_state_dirs
  if "$@" >>"$INSTALL_LOG" 2>&1; then
    return 0
  fi
  error "$label 失败，详情见 $INSTALL_LOG"
}

usage() {
  cat <<EOF
僵尸危机安装与本地服务管理

用法:
  install      安装/更新并启动游戏（默认）
  upgrade      升级游戏；如果服务正在运行，会自动重启
  start        后台启动游戏服务
  stop         停止游戏服务
  restart      重启游戏服务
  status       查看服务状态
  open         打开游戏网页
  logs         查看服务日志
  version      查看本地和远端版本
  uninstall    停止服务并删除游戏与本地状态
  help         显示帮助

远程示例:
  /bin/bash -c "\$(curl -fsSL https://raw.githubusercontent.com/hellojuantu/zombie_crisis/refs/heads/main/install.sh)"
  /bin/bash -c "\$(curl -fsSL https://raw.githubusercontent.com/hellojuantu/zombie_crisis/refs/heads/main/install.sh)" -- upgrade
  /bin/bash -c "\$(curl -fsSL https://raw.githubusercontent.com/hellojuantu/zombie_crisis/refs/heads/main/install.sh)" -- uninstall

本地命令:
  $CONTROL_BIN start
  $CONTROL_BIN stop
  $CONTROL_BIN restart
  $CONTROL_BIN status
  $CONTROL_BIN version

安装目录: $INSTALL_DIR
状态目录: $STATE_DIR
日志目录: $LOG_DIR
EOF
}

resolve_command() {
  if [ "${1:-}" = "--" ]; then
    shift
  fi

  local command="${1:-}"
  if [ -z "$command" ]; then
    local invoked
    invoked="$(basename "$0")"
    case "$invoked" in
      install|upgrade|update|start|stop|restart|status|open|logs|version|uninstall|remove|help|-h|--help)
        command="$invoked"
        ;;
      *)
        command="install"
        ;;
    esac
  fi
  echo "$command"
}

check_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    error "未找到 python3，请先安装 Python 3.10+"
  fi
  local pyver
  pyver="$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>/dev/null || true)"
  if ! python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
    error "需要 Python 3.10+，当前版本: ${pyver:-未知}"
  fi
}

check_git() {
  if ! command -v git >/dev/null 2>&1; then
    error "未找到 git，请先安装 git"
  fi
}

trim_version() {
  sed -n '1p' | tr -d '\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

version_from_dir() {
  local dir="$1"
  if [ -f "$dir/VERSION" ]; then
    trim_version <"$dir/VERSION"
  fi
}

installed_version() {
  local version
  version="$(version_from_dir "$INSTALL_DIR")"
  if [ -n "$version" ]; then
    echo "$version"
    return 0
  fi
  if [ -f "$STATE_VERSION_FILE" ]; then
    version="$(trim_version <"$STATE_VERSION_FILE")"
    if [ -n "$version" ]; then
      echo "$version"
      return 0
    fi
  fi
  if [ -d "$INSTALL_DIR/.git" ]; then
    local rev
    rev="$(git -C "$INSTALL_DIR" rev-parse --short HEAD 2>/dev/null || true)"
    if [ -n "$rev" ]; then
      echo "未知旧版本($rev)"
    else
      echo "未知旧版本"
    fi
    return 0
  fi
  echo "未安装"
}

remote_version() {
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$REMOTE_VERSION_URL" 2>/dev/null | trim_version || true
  fi
}

save_installed_version() {
  ensure_state_dirs
  local version
  version="$(version_from_dir "$INSTALL_DIR")"
  if [ -n "$version" ]; then
    echo "$version" >"$STATE_VERSION_FILE"
  fi
}

ensure_checkout() {
  check_git
  ensure_state_dirs

  if [ -d "$INSTALL_DIR/.git" ]; then
    return 0
  fi
  if [ -e "$INSTALL_DIR" ]; then
    error "$INSTALL_DIR 已存在但不是僵尸危机 git 仓库，请移走后重试"
  fi

  info "正在安装游戏..."
  run_quiet "克隆游戏" git clone --quiet "$REPO_URL" "$INSTALL_DIR"
  save_installed_version
}

update_checkout() {
  check_git
  ensure_state_dirs
  local before
  local latest
  before="$(installed_version)"
  latest="$(remote_version)"
  if [ -n "$latest" ]; then
    info "当前版本: $before，最新版本: $latest"
  else
    info "当前版本: $before"
  fi

  if [ ! -d "$INSTALL_DIR/.git" ]; then
    ensure_checkout
    info "已安装版本: $(installed_version)"
    return 0
  fi

  info "正在更新游戏..."
  run_quiet "更新代码" git -C "$INSTALL_DIR" pull --ff-only --quiet
  save_installed_version
  local after
  after="$(installed_version)"
  if [ "$before" = "$after" ]; then
    info "版本已是最新: $after"
  else
    info "版本已更新: $before -> $after"
  fi
}

setup_runtime() {
  check_python
  ensure_checkout

  if [ ! -d "$INSTALL_DIR/.venv" ]; then
    info "创建运行环境..."
    run_quiet "创建虚拟环境" python3 -m venv "$INSTALL_DIR/.venv"
  fi

  info "检查依赖..."
  PIP_DISABLE_PIP_VERSION_CHECK=1 run_quiet "安装依赖" \
    "$INSTALL_DIR/.venv/bin/python" -m pip install --disable-pip-version-check -q -r "$INSTALL_DIR/requirements.txt"
  save_installed_version
}

install_control_command() {
  ensure_state_dirs
  if [ -f "$INSTALL_DIR/install.sh" ]; then
    cp "$INSTALL_DIR/install.sh" "$CONTROL_BIN"
    chmod +x "$CONTROL_BIN"
  fi
}

pid_from_file() {
  if [ -f "$PID_FILE" ]; then
    sed -n '1p' "$PID_FILE"
  fi
}

pid_is_running() {
  local pid="$1"
  [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1
}

service_pid() {
  local pid
  pid="$(pid_from_file)"
  if pid_is_running "$pid"; then
    echo "$pid"
  fi
}

find_extra_server_pids() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -f "$INSTALL_DIR/server_asgi.py" 2>/dev/null || true
  fi
}

wait_for_url() {
  local timeout="${1:-20}"
  python3 - "$URL" "$timeout" <<'PY'
import sys
import time
import urllib.request

url = sys.argv[1]
timeout = float(sys.argv[2])
deadline = time.time() + timeout

while time.time() < deadline:
    try:
        with urllib.request.urlopen(url, timeout=0.8) as response:
            if 200 <= response.status < 500:
                sys.exit(0)
    except Exception:
        pass
    time.sleep(0.25)

sys.exit(1)
PY
}

open_browser() {
  if command -v open >/dev/null 2>&1; then
    open "$URL" >/dev/null 2>&1 &
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
  else
    warn "未找到可用的浏览器打开命令，请手动访问 $URL"
  fi
}

open_when_ready() {
  info "等待游戏服务就绪..."
  if wait_for_url 25; then
    info "游戏已启动: $URL"
    open_browser
  else
    warn "服务启动较慢，请稍后手动访问 $URL；日志见 $SERVER_LOG"
  fi
}

start_server() {
  setup_runtime
  install_control_command

  local pid
  pid="$(service_pid)"
  if [ -n "$pid" ]; then
    info "游戏服务已在运行，PID: $pid"
    open_when_ready
    return 0
  fi
  rm -f "$PID_FILE"

  if wait_for_url 1; then
    warn "检测到 $URL 已可访问，可能已有游戏服务正在运行"
    open_browser
    return 0
  fi

  ensure_state_dirs
  printf '\n[%s] start zombie_crisis\n' "$(date '+%Y-%m-%d %H:%M:%S')" >>"$SERVER_LOG"
  (
    cd "$INSTALL_DIR"
    export PYTHONUNBUFFERED=1
    exec nohup "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/server_asgi.py"
  ) >>"$SERVER_LOG" 2>&1 &

  pid="$!"
  echo "$pid" >"$PID_FILE"
  sleep 0.4
  if ! pid_is_running "$pid"; then
    rm -f "$PID_FILE"
    error "服务启动失败，详情见 $SERVER_LOG"
  fi

  info "后台服务 PID: $pid"
  open_when_ready
}

stop_server() {
  ensure_state_dirs

  local pids=""
  local pid
  pid="$(service_pid)"
  if [ -n "$pid" ]; then
    pids="$pid"
  fi

  local extra
  extra="$(find_extra_server_pids)"
  for pid in $extra; do
    case " $pids " in
      *" $pid "*) ;;
      *) pids="$pids $pid" ;;
    esac
  done

  if [ -z "$(echo "$pids" | tr -d ' ')" ]; then
    rm -f "$PID_FILE"
    warn "游戏服务未运行"
    return 0
  fi

  info "正在停止游戏服务..."
  for pid in $pids; do
    kill "$pid" >/dev/null 2>&1 || true
  done

  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    local alive=""
    for pid in $pids; do
      if pid_is_running "$pid"; then
        alive="$alive $pid"
      fi
    done
    [ -z "$alive" ] && break
    sleep 0.3
  done

  for pid in $pids; do
    if pid_is_running "$pid"; then
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  done

  rm -f "$PID_FILE"
  info "游戏服务已停止"
}

install_game() {
  update_checkout
  start_server
}

upgrade_game() {
  local was_running=0
  if [ -n "$(service_pid)" ]; then
    was_running=1
    stop_server
  fi

  update_checkout
  setup_runtime
  install_control_command

  if [ "$was_running" -eq 1 ]; then
    start_server
  else
    info "升级完成。使用 $CONTROL_BIN start 启动游戏。"
  fi
}

restart_server() {
  stop_server
  start_server
}

print_versions() {
  ensure_state_dirs
  local current
  local latest
  current="$(installed_version)"
  latest="$(remote_version)"
  echo "当前版本: $current"
  if [ -n "$latest" ]; then
    echo "最新版本: $latest"
  else
    echo "最新版本: 未知（无法读取远端 VERSION）"
  fi
}

status_server() {
  ensure_state_dirs
  local pid
  pid="$(service_pid)"
  if [ -n "$pid" ]; then
    info "游戏服务运行中，PID: $pid"
  else
    warn "游戏服务未运行"
  fi
  echo "版本: $(installed_version)"
  echo "网页地址: $URL"
  echo "安装目录: $INSTALL_DIR"
  echo "状态目录: $STATE_DIR"
  echo "服务日志: $SERVER_LOG"
  echo "安装日志: $INSTALL_LOG"
  echo "本地命令: $CONTROL_BIN"
}

show_logs() {
  ensure_state_dirs
  touch "$SERVER_LOG"
  tail -n 80 -f "$SERVER_LOG"
}

uninstall_game() {
  stop_server || true
  rm -rf "$INSTALL_DIR"
  rm -rf "$STATE_DIR"
  info "卸载完成，已删除 $INSTALL_DIR 和 $STATE_DIR"
}

COMMAND="$(resolve_command "$@")"

case "$COMMAND" in
  install|"")
    install_game
    ;;
  upgrade|update)
    upgrade_game
    ;;
  start)
    start_server
    ;;
  stop)
    stop_server
    ;;
  restart)
    restart_server
    ;;
  status)
    status_server
    ;;
  open)
    if wait_for_url 5; then
      open_browser
    else
      error "游戏服务未就绪，请先运行 $CONTROL_BIN start"
    fi
    ;;
  logs)
    show_logs
    ;;
  version)
    print_versions
    ;;
  uninstall|remove)
    uninstall_game
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    usage
    error "未知命令: $COMMAND"
    ;;
esac
