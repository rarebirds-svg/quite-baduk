# Baduk E2E Tests

```bash
npm install
npm run install-browsers

# Boot a native backend + web stack with KATAGO_MOCK. Alt ports avoid
# colliding with the launchd prod stack on 8000/3000.
BADUK_API_PORT=18000 BADUK_WEB_PORT=13000 bash scripts/start-stack.sh

PLAYWRIGHT_BASE_URL=http://localhost:13000 npm test

bash scripts/stop-stack.sh
```

CI (GitHub Actions) uses the same `start-stack.sh` with default ports 8000/3000 (no launchd, no conflict).
