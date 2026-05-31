#!/usr/bin/env bash
# 맥미니 머신 레벨 자동 복구 설정 — 정전 자동부팅·슬립 금지·자동로그인 안내를 적용한다.
set -euo pipefail

if [ "$(uname)" != "Darwin" ]; then
  echo "이 스크립트는 macOS 전용입니다." >&2
  exit 1
fi

echo "== pmset 전원 정책 적용 (sudo 필요) =="
# 정전 복구 시 자동 부팅
sudo pmset -a autorestart 1
# 슬립·디스크 슬립 금지 (24/7 서비스)
sudo pmset -a sleep 0 disksleep 0
# Wake on network access 허용
sudo pmset -a womp 1 || true

echo
echo "== 현재 pmset 설정 =="
pmset -g | grep -E 'autorestart|(^| )sleep|disksleep|womp' || true

echo
echo "== 수동 1회 설정 (스크립트로 자동화 불가) =="
echo "  자동 로그인을 켜야 재부팅 후 GUI LaunchAgent(com.baduk.*)가 사람 개입 없이 기동됩니다."
echo "  시스템 설정 → 사용자 및 그룹 → 자동 로그인 → 이 계정 선택."
echo "  (cloudflared는 LaunchDaemon이라 로그인과 무관하게 부팅 시 기동됩니다.)"
