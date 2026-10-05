#!/usr/bin/env bash
# 같은 키의 알림을 날짜당 1회로 억제하는 공용 헬퍼 (ops-report send.py의 once_key 규약을 bash로 옮김, run-*.sh·watchdog가 source).

# $1=중복 억제 키, $2=메시지.
# 마커가 있으면 발송을 건너뛰고 0. 없으면 발송하고, 성공했을 때만 마커를 남긴다(실패 시 다음 호출이 재시도).
# NOTIFY 기본값이 상대경로라 호출측 cwd가 리포 루트여야 한다 — 기존 run-*.sh는 모두 루트로 cd한 뒤 동작한다.
notify_once() {
  local key="$1" message="$2"
  local marker_dir="${MARKER_DIR:-$HOME/.ops-report/markers}"
  local day="${NOTIFY_ONCE_DATE:-$(date +%Y-%m-%d)}"
  local marker="$marker_dir/notify-once-$key-$day"
  local rc=0

  mkdir -p "$marker_dir"
  if [ -f "$marker" ]; then return 0; fi

  "${NOTIFY:-ops/notify.sh}" "$message" || rc=$?
  if [ "$rc" -ne 0 ]; then return "$rc"; fi

  : > "$marker"
}
