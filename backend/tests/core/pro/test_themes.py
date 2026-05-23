# 테마 카탈로그·필터 매핑 단위 테스트.
from app.core.pro.themes import THEMES, theme_by_slug, theme_query_clause


def test_themes_catalog_has_required_keys():
    assert len(THEMES) >= 5
    for t in THEMES:
        assert set(t.keys()) >= {"slug", "label", "description", "filter_type", "filter_value"}
        assert t["slug"] and isinstance(t["slug"], str)
        assert t["filter_type"] in {"collection", "event_like", "event_exact", "date_gte"}


def test_themes_slugs_unique():
    slugs = [t["slug"] for t in THEMES]
    assert len(slugs) == len(set(slugs))


def test_theme_by_slug_found_and_missing():
    assert theme_by_slug("masterpieces") is not None
    assert theme_by_slug("masterpieces")["slug"] == "masterpieces"
    assert theme_by_slug("does-not-exist") is None


def test_theme_query_clause_known_slug_returns_clause():
    clause = theme_query_clause("masterpieces")
    assert clause is not None  # SQLAlchemy BinaryExpression


def test_theme_query_clause_unknown_slug_returns_none():
    assert theme_query_clause("does-not-exist") is None


def test_theme_query_clause_all_catalog_slugs_resolvable():
    # 카탈로그 모든 슬러그가 clause 반환해야 함.
    for t in THEMES:
        clause = theme_query_clause(t["slug"])
        assert clause is not None, f"slug {t['slug']} returned None clause"
