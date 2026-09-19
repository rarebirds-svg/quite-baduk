// 프로 기보 목록의 페이지 크기와 첫 화면 질의 상수 — 서버 페이지와 클라이언트 목록이 함께 쓰므로 "use client" 없이 둔다.
export const PAGE_SIZE = 50;

// 서버가 미리 받아올 첫 화면 질의 — ProGameList의 초기 state와 한 글자도 어긋나면 안 되므로
// 같은 상수에서 만들어 둔다. "use client" 모듈에서 export하면 RSC 서버 번들에서
// 클라이언트 참조 객체로 바뀌어 `[object Object]`로 직렬화된다(#99).
export const PRO_LIST_INITIAL_QUERY = new URLSearchParams({
  collection: "masterpiece",
  sort: "recent",
  limit: String(PAGE_SIZE),
  offset: "0",
}).toString();
