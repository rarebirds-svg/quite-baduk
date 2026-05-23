// 이 달의 명국 인덱스 — 최근 12개월 + 현재 + 다음 달 픽 리스트.
import type { Metadata } from "next";

const BASE = "https://inkbaduk.com";

export const metadata: Metadata = {
  title: "이 달의 명국 — inkbaduk",
  description: "매월 결정적 알고리즘으로 고른 inkbaduk의 이 달의 명국 픽.",
  alternates: { canonical: `${BASE}/spectate/picks` },
};

function monthList(): string[] {
  const now = new Date();
  const months: string[] = [];
  for (let delta = -12; delta <= 1; delta++) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + delta, 1));
    months.push(
      `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`,
    );
  }
  return months;
}

export default function PicksIndex() {
  const months = monthList();
  return (
    <article className="prose">
      <h1>이 달의 명국</h1>
      <p>매월 결정적 알고리즘으로 한 게임을 고릅니다. 같은 달은 같은 픽.</p>
      <ul className="not-prose grid gap-1">
        {months.map((m) => {
          const [y, mm] = m.split("-");
          return (
            <li key={m}>
              <a href={`/spectate/picks/monthly/${m}`}>
                {y}년 {Number(mm)}월
              </a>
            </li>
          );
        })}
      </ul>
    </article>
  );
}
