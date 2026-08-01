# CWI 자동 수집 스크립트의 단위 테스트.
from __future__ import annotations

import hashlib

import httpx
import pytest

from scripts.ingest_cwi_weekly import (
    crawl_sgf_links,
    extract_sgf_links,
    extract_subdir_links,
    is_cwi_url,
)


def test_is_cwi_url_allows_cwi():
    assert is_cwi_url("https://homepages.cwi.nl/~aeb/go/games/foo.sgf") is True
    assert is_cwi_url("http://homepages.cwi.nl/~aeb/go/games/sub/bar.sgf") is True


def test_is_cwi_url_rejects_others():
    assert is_cwi_url("https://gokifu.com/foo.sgf") is False
    assert is_cwi_url("https://example.com/foo.sgf") is False
    assert is_cwi_url("https://homepages.cwi.nl/other/path.sgf") is False
    assert is_cwi_url("file:///etc/passwd") is False


def test_extract_sgf_links_returns_absolute_cwi_urls():
    html = (
        '<html><body>'
        '<a href="games/foo.sgf">foo</a>'
        '<a href="bar.html">bar</a>'
        '<a href="baz.sgf">baz</a>'
        '<a href="https://evil.com/danger.sgf">danger</a>'
        '</body></html>'
    )
    base = "https://homepages.cwi.nl/~aeb/go/games/"
    links = extract_sgf_links(html, base)
    assert "https://homepages.cwi.nl/~aeb/go/games/games/foo.sgf" in links
    assert "https://homepages.cwi.nl/~aeb/go/games/baz.sgf" in links
    assert all(is_cwi_url(u) for u in links)
    assert "https://evil.com/danger.sgf" not in links
    assert not any(u.endswith(".html") for u in links)


def test_extract_subdir_links_returns_cwi_dirs_only():
    html = (
        '<html><body>'
        '<a href="games/Agon/">Agon</a>'
        '<a href="?C=N;O=A">sort</a>'
        '<a href="/~aeb/go/">parent</a>'
        '<a href="foo.sgf">file</a>'
        '<a href="https://evil.com/x/">evil</a>'
        '</body></html>'
    )
    base = "https://homepages.cwi.nl/~aeb/go/games/"
    dirs = extract_subdir_links(html, base)
    assert dirs == ["https://homepages.cwi.nl/~aeb/go/games/games/Agon/"]


_BASE = "https://homepages.cwi.nl/~aeb/go/games/"


def _tree_handler():
    pages = {
        _BASE: '<a href="games/sub1/">sub1</a><a href="top.sgf">t</a>',
        _BASE + "games/sub1/": (
            '<a href="deep/">deep</a><a href="a.sgf">a</a><a href="../">up</a>'
        ),
        _BASE + "games/sub1/deep/": '<a href="b.sgf">b</a>',
    }
    def handler(request):
        url = str(request.url)
        if url in pages:
            return httpx.Response(200, text=pages[url])
        if url.endswith(".sgf"):
            return httpx.Response(200, text="(;FF[4]SZ[19];B[pd])")
        return httpx.Response(404)
    return handler


@pytest.mark.asyncio
async def test_crawl_finds_nested_sgfs():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_tree_handler())) as http:
        links = await crawl_sgf_links(http, _BASE, max_depth=4, max_pages=50)
    assert _BASE + "top.sgf" in links
    assert _BASE + "games/sub1/a.sgf" in links
    assert _BASE + "games/sub1/deep/b.sgf" in links


@pytest.mark.asyncio
async def test_crawl_respects_max_depth():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_tree_handler())) as http:
        links = await crawl_sgf_links(http, _BASE, max_depth=1, max_pages=50)
    assert _BASE + "games/sub1/a.sgf" in links
    assert _BASE + "games/sub1/deep/b.sgf" not in links


@pytest.mark.asyncio
async def test_crawl_respects_max_pages():
    async with httpx.AsyncClient(transport=httpx.MockTransport(_tree_handler())) as http:
        links = await crawl_sgf_links(http, _BASE, max_depth=4, max_pages=1)
    assert links == [_BASE + "top.sgf"]


def test_index_hash_skips_when_unchanged(tmp_path, monkeypatch):
    """index 페이지가 변경되지 않았으면 (캐시 일치) ingest는 변경 없음."""
    monkeypatch.setenv("HOME", str(tmp_path))
    import scripts.ingest_cwi_weekly as mod
    # CACHE_PATH는 모듈 로드 시 평가되므로 monkeypatch 후 재계산
    monkeypatch.setattr(mod, "CACHE_PATH", tmp_path / ".baduk" / "ingest-cwi.cache")

    html = "<html><a href='foo.sgf'>foo</a></html>"
    mod.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    mod.CACHE_PATH.write_text(hashlib.md5(html.encode("utf-8"), usedforsecurity=False).hexdigest())

    assert mod.index_changed(html) is False  # 캐시와 동일 → 변경 없음
    # 다른 콘텐츠는 변경됨
    assert mod.index_changed("<html>different</html>") is True


def test_save_index_hash_writes_md5(tmp_path, monkeypatch):
    import scripts.ingest_cwi_weekly as mod
    monkeypatch.setattr(mod, "CACHE_PATH", tmp_path / ".baduk" / "ingest-cwi.cache")
    html = "<html>test</html>"
    mod.save_index_hash(html)
    assert mod.CACHE_PATH.exists()
    expected = hashlib.md5(html.encode("utf-8"), usedforsecurity=False).hexdigest()
    assert mod.CACHE_PATH.read_text() == expected


@pytest.mark.asyncio
async def test_main_async_caps_new_and_skips_hash(tmp_path, monkeypatch):
    import scripts.ingest_cwi_weekly as mod
    monkeypatch.setattr(mod, "CACHE_PATH", tmp_path / ".baduk" / "ingest-cwi.cache")
    monkeypatch.setattr(mod, "MAX_NEW_PER_RUN", 2)

    base = "https://homepages.cwi.nl/~aeb/go/games/"
    index_html = "".join(f'<a href="g{i}.sgf">g{i}</a>' for i in range(4))

    def handler(request):
        url = str(request.url)
        if url == base:
            return httpx.Response(200, text=index_html)
        if url.endswith(".sgf"):
            n = url.rstrip(".sgf")[-1]
            return httpx.Response(200, text=f"(;FF[4]GM[1]SZ[19]EV[E{n}];B[pd];W[dc])")
        return httpx.Response(404)

    real_client = httpx.AsyncClient
    def patched_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        kwargs.pop("follow_redirects", None)
        return real_client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    import app.models  # noqa: F401
    from app.db import Base
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    monkeypatch.setattr(
        mod, "AsyncSessionLocal",
        async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession),
    )

    summary = await mod.main_async()
    assert summary["new"] == 2
    assert mod.CACHE_PATH.exists() is False


@pytest.mark.asyncio
async def test_main_async_ingests_new_sgfs(tmp_path, monkeypatch):
    """index → SGF → parse → insert 전체 경로. httpx.MockTransport로 모킹."""
    import scripts.ingest_cwi_weekly as mod
    monkeypatch.setattr(mod, "CACHE_PATH", tmp_path / ".baduk" / "ingest-cwi.cache")

    index_html = (
        '<a href="game1.sgf">g1</a>'
        '<a href="game2.sgf">g2</a>'
    )
    sgf_body = (
        b"(;FF[4]GM[1]SZ[19]KM[6.5]"
        b"PB[Black]BR[7d]PW[White]WR[9p]"
        b"EV[Test Event]DT[2024-01-01]RE[B+R]"
        b";B[pd];W[dc])"
    )

    base = "https://homepages.cwi.nl/~aeb/go/games/"

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == base:
            return httpx.Response(200, text=index_html)
        if url.endswith(".sgf"):
            return httpx.Response(200, content=sgf_body)
        return httpx.Response(404)

    # AsyncClient를 가로채 MockTransport 주입
    import httpx
    real_client = httpx.AsyncClient
    def patched_client(*args, **kwargs):
        kwargs.pop("timeout", None)
        kwargs.pop("follow_redirects", None)
        return real_client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    # DB를 테스트용 인메모리 DB로 교체
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    import app.models  # noqa: F401
    from app.db import Base
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    test_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    monkeypatch.setattr(mod, "AsyncSessionLocal", test_session)

    summary = await mod.main_async()
    assert summary["fetched"] == 2
    # 같은 SGF 본문이라 content_hash가 같음 → 하나는 신규, 하나는 중복
    assert summary["new"] + summary["duplicate"] == 2
    assert summary["error"] == 0
