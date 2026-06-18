#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/var/log/myapp}"
ARCHIVE_DIR="${ARCHIVE_DIR:-${LOG_DIR}/archive}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$ARCHIVE_DIR"

today=$(date -u +%Y-%m-%d)
yesterday=$(date -u -d '1 day ago' +%Y-%m-%d 2>/dev/null || date -u -v-1d +%Y-%m-%d)

if [ -f "$LOG_DIR/app.log" ]; then
  cp "$LOG_DIR/app.log" "$ARCHIVE_DIR/app-$yesterday.log"
  : > "$LOG_DIR/app.log"
  gzip -f "$ARCHIVE_DIR/app-$yesterday.log"
fi

find "$ARCHIVE_DIR" -type f -name 'app-*.log.gz' -mtime "+$RETENTION_DAYS" -print -delete
