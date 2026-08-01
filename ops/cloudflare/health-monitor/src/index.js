// Cron 트리거로 공개 /api/health를 폴링하고 실패 시 Telegram으로 알린다.
async function notify(env, text) {
  const url = `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/sendMessage`;
  await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text }),
  });
}

async function probe(env) {
  try {
    const res = await fetch(env.HEALTH_URL, {
      signal: AbortSignal.timeout(10000),
    });
    if (!res.ok) return `HTTP ${res.status}`;
    const body = await res.json();
    if (body.status !== "ok") return `status=${body.status} db=${body.db} katago=${body.katago_alive}`;
    return null; // 정상
  } catch (e) {
    return `unreachable: ${e.name}`;
  }
}

export default {
  async scheduled(_event, env, _ctx) {
    const problem = await probe(env);
    if (problem) {
      await notify(env, `[inkbaduk] 외부 모니터 — ${env.HEALTH_URL} 이상: ${problem}`);
    }
  },
  // 수동 점검용 HTTP 진입점 (`curl <worker-url>`)
  async fetch(_req, env) {
    const problem = await probe(env);
    return new Response(problem ? `FAIL: ${problem}` : "OK", { status: problem ? 503 : 200 });
  },
};
