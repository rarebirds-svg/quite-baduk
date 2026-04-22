"""Tests for the in-memory NicknameRegistry."""
from __future__ import annotations

import asyncio

import pytest

from app.session_registry import NicknameRegistry


@pytest.mark.asyncio
async def test_claim_returns_true_for_fresh_key():
    r = NicknameRegistry()
    assert await r.claim("alice", 1) is True


@pytest.mark.asyncio
async def test_claim_returns_false_for_taken_key():
    r = NicknameRegistry()
    await r.claim("alice", 1)
    assert await r.claim("alice", 2) is False


@pytest.mark.asyncio
async def test_release_frees_the_key():
    r = NicknameRegistry()
    await r.claim("alice", 1)
    await r.release("alice")
    assert await r.claim("alice", 2) is True


@pytest.mark.asyncio
async def test_is_taken_reflects_state():
    r = NicknameRegistry()
    assert await r.is_taken("alice") is False
    await r.claim("alice", 1)
    assert await r.is_taken("alice") is True
    await r.release("alice")
    assert await r.is_taken("alice") is False


@pytest.mark.asyncio
async def test_concurrent_claims_only_one_wins():
    r = NicknameRegistry()

    async def try_claim(sid: int) -> bool:
        return await r.claim("alice", sid)

    results = await asyncio.gather(*[try_claim(i) for i in range(20)])
    assert results.count(True) == 1
    assert results.count(False) == 19


@pytest.mark.asyncio
async def test_release_unknown_key_is_noop():
    r = NicknameRegistry()
    # Should not raise
    await r.release("nobody")
