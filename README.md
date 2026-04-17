# AI 바둑 (AI Go)

A web application to play the game of Go against the KataGo AI engine. Supports rank selection from 18k to 7d and handicap games with 2–9 stones.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/)

## Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

## Access

| Service  | URL                      |
|----------|--------------------------|
| Frontend | http://localhost:3000    |
| API      | http://localhost:8000    |

## First Time

1. Sign up at [/signup](http://localhost:3000/signup)
2. Go to [/game/new](http://localhost:3000/game/new) to start a game

## Environment Variables

| Variable       | Required in prod | Default                    | Description                                      |
|----------------|-----------------|----------------------------|--------------------------------------------------|
| `JWT_SECRET`   | Yes             | `changeme-in-production`   | Secret key used to sign JWT tokens               |
| `KATAGO_MOCK`  | No              | `false`                    | Set to `true` for local dev without KataGo binary |

Copy `.env.example` to `.env` and update values before deploying to production.

## Backup

Game data is automatically backed up daily to the `backups/` Docker volume with 30-day retention. Backup files are named `baduk-YYYY-MM-DD.db`.

## Troubleshooting

**KataGo model download failure**

If the KataGo model fails to download at startup, set `KATAGO_MOCK=true` in your `.env` file to run with a mock AI engine for local development:

```bash
echo "KATAGO_MOCK=true" >> .env
docker-compose up --build
```

**Port conflicts**

If ports 3000 or 8000 are already in use, stop the conflicting services or edit `docker-compose.yml` to map to different host ports (e.g., `"3001:3000"`).

## License

MIT
