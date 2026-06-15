#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${PROJECT_DIR}/dist"
FNPACK_BIN="${FNPACK_BIN:-}"

manifest_value() {
  local key="$1"
  awk -F= -v key="$key" '$1 ~ "^[[:space:]]*" key "[[:space:]]*$" { gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit }' "${PROJECT_DIR}/manifest"
}

if [[ -z "${FNPACK_BIN}" ]]; then
  if command -v fnpack >/dev/null 2>&1; then
    FNPACK_BIN="$(command -v fnpack)"
  else
    FNPACK_BIN="$(find "${PROJECT_DIR}" "${PROJECT_DIR}/tools" -maxdepth 1 -type f -name 'fnpack*' 2>/dev/null | head -n 1 || true)"
  fi
fi

if [[ -z "${FNPACK_BIN}" || ! -x "${FNPACK_BIN}" ]]; then
  echo "找不到可执行的 fnpack。请设置 FNPACK_BIN=/abs/path/to/fnpack，或把 fnpack 放到项目根目录并 chmod +x。" >&2
  exit 1
fi

mkdir -p "${DIST_DIR}"
rm -f "${PROJECT_DIR}"/*.fpk

"${FNPACK_BIN}" build --directory "${PROJECT_DIR}"

APPNAME="$(manifest_value appname)"
VERSION="$(manifest_value version)"
BUILT="${PROJECT_DIR}/${APPNAME}.fpk"
if [[ ! -f "${BUILT}" ]]; then
  BUILT="$(find "${PROJECT_DIR}" -maxdepth 1 -name '*.fpk' | head -n 1 || true)"
fi

if [[ -z "${BUILT}" || ! -f "${BUILT}" ]]; then
  echo "fnpack 没有生成 .fpk 文件。" >&2
  exit 1
fi

TARGET="${DIST_DIR}/${APPNAME}-${VERSION}.fpk"
mv -f "${BUILT}" "${TARGET}"
echo "FPK generated: ${TARGET}"
