# inkbaduk 외부 헬스 모니터

맥미니 *밖*(Cloudflare 엣지)에서 5분마다 `/api/health`를 폴링해 실패 시 Telegram으로
알린다. 맥미니가 통째로 죽어도(머신·네트워크·Tunnel 다운) 이 감시자는 살아 있다.

## 배포

```bash
cd ops/cloudflare/health-monitor
npm i -g wrangler            # 최초 1회
wrangler login              # 브라우저 인증

# 시크릿 등록 (값은 ~/.claude/channels/telegram/.env, ops/ops.env 참조)
wrangler secret put TELEGRAM_BOT_TOKEN
wrangler secret put TELEGRAM_CHAT_ID

wrangler deploy
```

## 로컬 검증

```bash
# scheduled 핸들러 테스트 (정상이면 알림 없음, 이상이면 Telegram 발송)
wrangler dev --test-scheduled
curl "http://localhost:8787/__scheduled?cron=*/5+*+*+*+*"

# HTTP 진입점으로 즉시 상태 확인
curl http://localhost:8787    # OK 또는 FAIL: <이유>
```

## 검증 기준

cloudflared를 내려 origin을 죽인 뒤 5분 내 Telegram 알림 수신.
