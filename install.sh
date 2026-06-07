#!/bin/bash
set -e

REPO_URL="https://github.com/hellojuantu/zombie_crisis.git"
INSTALL_DIR="$HOME/zombie_crisis"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[僵尸危机]${NC} $1"; }
warn()  { echo -e "${YELLOW}[警告]${NC} $1"; }
error() { echo -e "${RED}[错误]${NC} $1"; exit 1; }

# Python check
if ! command -v python3 &>/dev/null; then
  error "未找到 python3，请先安装 Python 3.10+"
fi
PYVER=$(python3 -c "import sys; print(sys.version_info[:2])" 2>/dev/null)
if ! python3 -c "import sys; assert sys.version_info >= (3,10)" 2>/dev/null; then
  error "需要 Python 3.10+，当前版本: $PYVER"
fi

# Git check·
if ! command -v git &>/dev/null; then
  error "未找到 git，请先安装 git"
fi

# Clone or upgrade
if [ -d "$INSTALL_DIR/.git" ]; then
  info "检测到已有安装，正在升级..."
  git -C "$INSTALL_DIR" pull --ff-only || warn "升级失败（可能有本地修改），跳过"
else
  info "正在克隆游戏..."
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Venv
if [ ! -d ".venv" ]; then
  info "创建虚拟环境..."
  python3 -m venv .venv
fi
source .venv/bin/activate

# Deps
info "安装依赖..."
pip install -q -r requirements.txt

# Open browser
URL="http://localhost:8080/"
if command -v open &>/dev/null; then
  (sleep 1.5 && open "$URL") &
elif command -v xdg-open &>/dev/null; then
  (sleep 1.5 && xdg-open "$URL") &
fi

info "启动游戏服务... 打开浏览器访问 $URL"
info "单人静态版本：${URL}solo"
python3 server_asgi.py
