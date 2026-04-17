# Changelog

## [0.1.0] - 2026-04-17

Initial release — MVP.

### Features
- Web-based Go board (19x19 SVG)
- Account system (email + password, JWT HttpOnly cookie)
- Rank selection: 18k, 15k, 12k, 10k, 7k, 5k, 3k, 1k, 1d, 3d, 5d, 7d (KataGo Human-SL model)
- Handicap games: 2–9 stones, Korean rules (komi 0.5)
- Even games: komi 6.5
- In-game actions: move, pass, resign, undo (2 plies), hint (top-3 winrate)
- Automatic rule enforcement: ko, suicide, capture
- Territory scoring (Korean rules)
- Game review: move-by-move replay + position analysis (winrate, top moves, ownership)
- SGF export (download)
- Personal history and stats
- i18n: Korean and English
- Dark mode
- Single-session policy per game (WebSocket)
- Auto-restart of KataGo subprocess with state replay
- Daily SQLite backup with 30-day rolling retention

### Architecture
- Frontend: Next.js 14 (App Router, TypeScript, Tailwind)
- Backend: FastAPI (Python 3.11, SQLAlchemy 2, Alembic, Pydantic v2)
- AI engine: KataGo v1.15.3 (Eigen CPU build) + `b18c384nbt-humanv0` model
- Database: SQLite with WAL
- Real-time: WebSocket
- Deployment: Docker Compose (web + backend + backup services)

### Quality
- 170 backend tests (pytest), Rules Engine 100% line coverage
- 8 frontend tests (Vitest)
- 5 end-to-end scenarios (Playwright)
- 5-agent parallel code review — see `docs/QUALITY_REPORT.md`

### Known Limitations
- 19x19 only (9x9/13x13 deferred to V2)
- No time controls (byoyomi, Fischer)
- No user-vs-user games
- No social login / OAuth
- No admin console
- Rate limiting only on login/signup (not on move/analyze endpoints)

See `docs/QUALITY_REPORT.md` for the full list of open recommendations.
