# 러닝북: 백업 검증

- 주기: 매일 12시·18시 (오케스트레이터)
- 등급: 🟢 자율
- 목적: 로컬 백업이 신선하고 복원 가능한 상태인지 확인한다.

## 절차

### 1. 신선도

```bash
NEWEST=$(ls -1t ~/baduk-backups/daily/*.db.gz 2>/dev/null | head -1)
echo "최신 백업: ${NEWEST:-없음}"
[ -n "$NEWEST" ] && find "$NEWEST" -mtime +1 -print
```
판정: 최신 백업이 없거나, `find ... -mtime +1`이 파일을 출력하면(=30시간 이상 오래됨) 경보.

### 2. 티어 개수

```bash
for t in daily weekly monthly; do
  echo "$t: $(ls -1 ~/baduk-backups/$t/*.db.gz 2>/dev/null | wc -l | tr -d ' ')개"
done
```
판정: `daily`가 0개면 경보(백업 미생성). weekly·monthly는 0이어도 정상(아직 해당 요일/날짜가 안 옴).

### 3. 복원 드릴

```bash
NEWEST=$(ls -1t ~/baduk-backups/daily/*.db.gz 2>/dev/null | head -1)
DRILL=/tmp/baduk-restore-drill.db
rm -f "$DRILL"
gunzip -c "$NEWEST" > "$DRILL"
sqlite3 "$DRILL" "PRAGMA integrity_check;"
sqlite3 "$DRILL" "SELECT count(*) FROM sqlite_master WHERE type='table';"
rm -f "$DRILL"
```
판정: `integrity_check`가 `ok`를 출력하고 테이블 수가 1 이상이면 정상. 그 외는 경보(백업 손상).

## 결과 처리

1. 결과를 `state/log/YYYY-MM-DD.md`에 추가한다.
2. `state/dashboard.md`의 백업 상태 행을 갱신한다.
3. 경보 사유가 있으면 `state/incidents.md`에 기록한다. Telegram 보고는
   오케스트레이터가 실행 요약으로 처리한다.
