# CWI 퍼블릭 도메인 컬렉션에서 신규 프로 SGF를 주1회 자동 ingest한다.
"""CWI 자동 수집 스크립트.

Usage (launchd가 호출):
    python -m scripts.ingest_cwi_weekly

소스: homepages.cwi.nl/~aeb/go/games/ 만 허용 (라이선스 정책 — pro-game-sgf-source 메모리).
캐시: ~/.baduk/ingest-cwi.cache 에 index 페이지 md5 저장.
중복: pro_games.content_hash로 차단.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import structlog
from sqlalchemy import select

from app.core.sgf.import_sgf import InvalidProSgf, ParsedProGame, parse_pro_sgf
from app.db import AsyncSessionLocal
from app.models import ProGame

log = structlog.get_logger()

CWI_INDEX_URL = "https://homepages.cwi.nl/~aeb/go/games/"
ALLOWED_HOSTS = {"homepages.cwi.nl"}
ALLOWED_PATH_PREFIX = "/~aeb/go/games/"
CACHE_PATH = Path.home() / ".baduk" / "ingest-cwi.cache"


def is_cwi_url(url: str) -> bool:
    """CWI 컬렉션 도메인+경로 화이트리스트. 라이선스 정책 강제."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.hostname not in ALLOWED_HOSTS:
        return False
    if not parsed.path.startswith(ALLOWED_PATH_PREFIX):
        return False
    return True


def extract_sgf_links(html: str, base_url: str) -> list[str]:
    """HTML에서 .sgf 링크를 절대 URL로 추출. CWI 도메인만 통과."""
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    out: list[str] = []
    for href in hrefs:
        if not href.lower().endswith(".sgf"):
            continue
        absolute = urljoin(base_url, href)
        if is_cwi_url(absolute):
            out.append(absolute)
    # dedup, preserve order
    return list(dict.fromkeys(out))


def extract_subdir_links(html: str, base_url: str) -> list[str]:
    """HTML에서 하위 디렉터리(/ 로 끝나는) 링크를 절대 URL로 추출. CWI만 통과.
    Apache 정렬 링크(?…)·상위(prefix 밖)·외부 도메인은 제외한다."""
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    out: list[str] = []
    for href in hrefs:
        if not href.endswith("/"):
            continue
        if href.startswith("?") or href.startswith("../") or href == "./":
            continue
        absolute = urljoin(base_url, href)
        if is_cwi_url(absolute):
            out.append(absolute)
    return list(dict.fromkeys(out))


async def crawl_sgf_links(
    http: httpx.AsyncClient,
    start_url: str,
    *,
    max_depth: int,
    max_pages: int,
) -> list[str]:
    """start_url에서 CWI 하위 디렉터리를 BFS로 따라가 .sgf 절대 URL을 수집한다.
    visited-set으로 순환 방지, max_depth/max_pages로 폭주 방지."""
    queue: list[tuple[str, int]] = [(start_url, 0)]
    visited: set[str] = set()
    found: list[str] = []
    pages = 0
    while queue and pages < max_pages:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            resp = await http.get(url)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:  # noqa: BLE001 — 디렉터리 1장 실패는 건너뛰고 계속
            log.warning("cwi.dir.fetch_failed", url=url, err=str(exc))
            continue
        pages += 1
        for sgf in extract_sgf_links(html, url):
            if sgf not in found:
                found.append(sgf)
        if depth < max_depth:
            for sub in extract_subdir_links(html, url):
                if sub not in visited:
                    queue.append((sub, depth + 1))
    return found


def index_changed(html: str) -> bool:
    """index 페이지 md5가 캐시와 다르면 True (재처리 필요)."""
    current = hashlib.md5(html.encode("utf-8"), usedforsecurity=False).hexdigest()
    if not CACHE_PATH.exists():
        return True
    cached = CACHE_PATH.read_text().strip()
    return cached != current


def save_index_hash(html: str) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(hashlib.md5(html.encode("utf-8"), usedforsecurity=False).hexdigest())


def _build_pro_game(parsed: ParsedProGame) -> ProGame | None:
    """parse_pro_sgf 결과에서 ProGame 인스턴스 생성. ProGame.from_parsed() 위임."""
    try:
        return ProGame.from_parsed(parsed, collection="cwi", source_note=CWI_INDEX_URL)
    except (AttributeError, TypeError) as exc:
        log.warning("cwi.progame.build_failed", err=str(exc))
        return None


async def main_async() -> dict[str, int]:
    """1회 ingest 루프. 결과 카운트 반환."""
    summary: dict[str, int] = {"fetched": 0, "new": 0, "duplicate": 0, "error": 0}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
        try:
            resp = await http.get(CWI_INDEX_URL)
            resp.raise_for_status()
            html = resp.text
        except Exception as exc:
            log.error("cwi.index.fetch_failed", err=str(exc))
            return summary

        if not index_changed(html):
            log.info("cwi.index.unchanged")
            return summary

        links = extract_sgf_links(html, CWI_INDEX_URL)
        async with AsyncSessionLocal() as db:
            for url in links:
                summary["fetched"] += 1
                try:
                    sgf_resp = await http.get(url)
                    sgf_resp.raise_for_status()
                    sgf_text = sgf_resp.text
                except Exception as exc:
                    log.warning("cwi.sgf.fetch_failed", url=url, err=str(exc))
                    summary["error"] += 1
                    continue

                try:
                    parsed = parse_pro_sgf(sgf_text)
                except InvalidProSgf as exc:
                    log.warning("cwi.sgf.parse_failed", url=url, err=str(exc))
                    summary["error"] += 1
                    continue

                existing = await db.execute(
                    select(ProGame.id).where(ProGame.content_hash == parsed.content_hash)
                )
                if existing.scalar() is not None:
                    summary["duplicate"] += 1
                    continue

                pro = _build_pro_game(parsed)
                if pro is None:
                    summary["error"] += 1
                    continue
                db.add(pro)
                summary["new"] += 1

            await db.commit()

    save_index_hash(html)
    log.info("cwi.ingest.complete", **summary)
    return summary


def main() -> int:
    summary = asyncio.run(main_async())
    print(
        f"CWI ingest 완료: fetched={summary['fetched']} new={summary['new']} "
        f"duplicate={summary['duplicate']} error={summary['error']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
