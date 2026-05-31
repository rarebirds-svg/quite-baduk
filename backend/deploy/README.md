# Production deployment (Mac mini)

This directory contains the runtime artifacts that turn the dev stack
into a 24/7 service on a Mac mini under launchd, exposed publicly via
Cloudflare Tunnel, with daily encrypted backups to R2.

## One-time setup

1. Build KataGo with the Metal backend:

   ```bash
   ./backend/katago/build_macos.sh
   ```

2. Create `~/.baduk.env` with the variables in [Environment variables](#environment-variables).

3. Customize the plist with absolute paths and load it:

   ```bash
   sed -e "s|__PROJECT_PATH__|$HOME/projects/baduk|g" \
       -e "s|__USER_HOME__|$HOME|g" \
       backend/deploy/com.baduk.api.plist \
       > ~/Library/LaunchAgents/com.baduk.api.plist
   launchctl load ~/Library/LaunchAgents/com.baduk.api.plist
   ```

4. Verify the API is reachable locally:

   ```bash
   curl -s http://127.0.0.1:8000/api/health
   tail -f ~/Library/Logs/baduk-api.log
   ```

## Reload after a deploy

```bash
launchctl kickstart -k gui/$(id -u)/com.baduk.api
```

## Cloudflare Tunnel

The Mac mini exposes nothing inbound; cloudflared talks outbound to
Cloudflare and Cloudflare proxies inbound HTTPS + WebSocket to the
local FastAPI process.

```bash
brew install cloudflared
cloudflared tunnel login                # browser opens; pick the domain
cloudflared tunnel create baduk         # note the UUID printed
```

Customize `cloudflared.yml`:

```bash
sed -e "s|__TUNNEL_UUID__|<uuid>|g" \
    -e "s|__USER_HOME__|$HOME|g" \
    -e "s|__DOMAIN__|<your domain>|g" \
    backend/deploy/cloudflared.yml \
    > /tmp/cloudflared.yml
```

Route DNS + install the system service:

```bash
cloudflared tunnel route dns baduk api.<domain>
cloudflared tunnel route dns baduk <domain>

sudo cloudflared service install
sudo mkdir -p /etc/cloudflared
sudo cp /tmp/cloudflared.yml /etc/cloudflared/config.yml
sudo cp ~/.cloudflared/<UUID>.json /etc/cloudflared/
sudo launchctl unload /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
sudo launchctl load   /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

Smoke test from a phone tethered off home Wi-Fi:

```bash
curl -s https://api.<domain>/api/health
```

## Daily R2 backup

`r2_backup.sh` produces an atomic SQLite snapshot, gzips it, uploads to
the `baduk-backups` R2 bucket via rclone, and prunes anything older
than 30 days.

```bash
brew install rclone
rclone config        # add a remote named `r2`, type s3, provider Cloudflare
```

Schedule via cron (`crontab -e`):

```
0 4 * * * /Users/<you>/projects/baduk/backend/deploy/r2_backup.sh \
    >> /Users/<you>/Library/Logs/baduk-backup.log 2>&1
```

Test manually once + verify with `rclone ls r2:baduk-backups/`.

Practice a restore drill before launch:

```bash
mkdir -p /tmp/restore-drill
rclone copy r2:baduk-backups/<latest>.db.gz /tmp/restore-drill/
gunzip /tmp/restore-drill/<latest>.db.gz
sqlite3 /tmp/restore-drill/<latest>.db "SELECT count(*) FROM games;"
```

## Environment variables

Source these from `~/.baduk.env`. Generate `SESSION_SECRET` with
`python3 -c "import secrets; print(secrets.token_hex(32))"`.

| Variable | Purpose |
|---|---|
| `APP_ENV=production` | Enables HSTS, secure cookie defaults |
| `SESSION_SECRET` | 32-byte random hex; rotate annually |
| `KATAGO_BIN_PATH` | Absolute path to `backend/katago/bin/katago` |
| `KATAGO_HUMAN_MODEL_PATH` | Absolute path to the `b18c384nbt-humanv0.bin.gz` model |
| `KATAGO_POOL_SIZE=4` | Pool worker count |
| `CORS_ORIGINS` | `https://<domain>,https://localhost,capacitor://localhost,ionic://localhost` |
| `COOKIE_SAMESITE=none` | Required for Capacitor WebViews |
| `CF_TRUSTED_PROXY=true` | Trust Cloudflare's `CF-Connecting-IP` header |
| `DATABASE_URL=sqlite+aiosqlite:///./data/baduk.db` | (default) |

## First-launch checklist

- [ ] `./backend/katago/build_macos.sh` succeeds; `katago benchmark` shows ≥ 200 visits/s on M4
- [ ] `~/.baduk.env` populated
- [ ] launchd service loaded; `curl 127.0.0.1:8000/api/health` returns ok
- [ ] cloudflared service running; `curl https://api.<domain>/api/health` returns ok from off-LAN
- [ ] Cron entry installed for `r2_backup.sh`
- [ ] At least one R2 backup exists in the bucket
- [ ] One restore drill verified
- [ ] `tail -f ~/Library/Logs/baduk-api.log` shows JSON structlog lines

## 머신 레벨 자동 복구 (필수)

launchd KeepAlive는 프로세스 종료만 복구한다. 정전·재부팅 후 머신이 사람 개입
없이 서비스로 복귀하려면 전원·로그인 설정이 필요하다.

```bash
backend/deploy/harden_macos.sh
```

- `pmset autorestart 1` — 정전 복구 시 자동 부팅
- `pmset sleep 0` — 슬립 금지
- **자동 로그인 수동 활성화** — 시스템 설정 → 사용자 및 그룹 → 자동 로그인.
  `com.baduk.*`는 GUI 도메인 LaunchAgent라 로그인이 있어야 기동된다.

검증: 맥미니를 강제 재부팅 → 사람 개입 0으로 `curl -s https://<domain>/api/health`가
200을 반환하는지 확인.
