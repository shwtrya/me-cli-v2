#!/usr/bin/env bash
set -euo pipefail

if command -v pkg >/dev/null 2>&1; then
  pkg update -y
  pkg install -y python python-pillow clang rust openssl libffi make

  if [[ -z "${ANDROID_API_LEVEL:-}" ]]; then
    ANDROID_API_LEVEL="$(getprop ro.build.version.sdk 2>/dev/null || true)"
    export ANDROID_API_LEVEL="${ANDROID_API_LEVEL:-24}"
  fi

  python -m pip install -U pip setuptools wheel
  python -m pip install -r requirements.txt
else
  echo "Unsupported environment. Please install Python 3.10+ and run:"
  echo "  python -m pip install -r requirements.txt"
fi
