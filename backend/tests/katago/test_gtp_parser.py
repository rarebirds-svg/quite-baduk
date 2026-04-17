from app.core.katago.adapter import parse_gtp


def test_parse_success():
    r = parse_gtp("= Q16\n\n")
    assert r.ok is True
    assert r.body == "Q16"
    assert r.id is None


def test_parse_error():
    r = parse_gtp("? illegal move\n\n")
    assert r.ok is False
    assert "illegal" in r.body


def test_parse_with_id():
    r = parse_gtp("=42 pass\n\n")
    assert r.ok is True
    assert r.body == "pass"
    assert r.id == 42


def test_parse_empty_body():
    r = parse_gtp("=\n\n")
    assert r.ok is True
    assert r.body == ""


def test_parse_multiline():
    r = parse_gtp("= line1\nline2\nline3\n\n")
    assert r.ok is True
    assert "line1" in r.body
    assert "line3" in r.body


def test_parse_garbage():
    r = parse_gtp("garbage no prefix")
    assert r.ok is False


def test_parse_empty():
    r = parse_gtp("")
    assert r.ok is False
