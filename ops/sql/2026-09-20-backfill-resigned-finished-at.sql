-- #101 이전에 사용자 기권으로 종료됐으나 finished_at이 NULL인 대국 99건을 일회성 백필한다 (AP-20260920-02).
-- 규칙: 마지막 수 시각(moves.max(played_at)), 수가 없으면 started_at. active·finished 행은 건드리지 않는다.
-- 실행: sqlite3 backend/data/baduk.db < ops/sql/2026-09-20-backfill-resigned-finished-at.sql
BEGIN;
UPDATE games
   SET finished_at = COALESCE(
         (SELECT MAX(played_at) FROM moves WHERE moves.game_id = games.id),
         started_at)
 WHERE status = 'resigned' AND finished_at IS NULL;
COMMIT;
