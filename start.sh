#!/bin/bash
set -e

if ! command -v python3 &>/dev/null || ! python3 -c "import sys; assert sys.version_info >= (3,10)" 2>/dev/null; then
  echo "需要 Python 3.10 或更高版本"
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt
python3 server_asgi.py
