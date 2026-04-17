from app.core.katago.analysis import parse_analysis


def test_parse_empty():
    r = parse_analysis("")
    assert r.top_moves == []
    assert r.ownership == []


def test_parse_single_move():
    body = "info move Q16 visits 100 winrate 0.523 scoreLead 1.5 prior 0.1\n"
    r = parse_analysis(body)
    assert len(r.top_moves) == 1
    hint = r.top_moves[0]
    assert hint.move == "Q16"
    assert hint.visits == 100
    assert abs(hint.winrate - 0.523) < 0.001
    assert abs(hint.score_lead - 1.5) < 0.001


def test_parse_multi_moves_sorted():
    body = "info move D4 visits 30 winrate 0.48 info move Q16 visits 100 winrate 0.52 info move Q4 visits 50 winrate 0.50\n"
    r = parse_analysis(body)
    assert [m.move for m in r.top_moves] == ["Q16", "Q4", "D4"]


def test_parse_winrate_from_top_move():
    body = "info move Q16 visits 100 winrate 0.7\n"
    r = parse_analysis(body)
    assert abs(r.winrate - 0.7) < 0.001


def test_parse_ownership():
    floats = " ".join(["0.5"] * 361)
    body = f"info move Q16 visits 100 winrate 0.5 ownership {floats}\n"
    r = parse_analysis(body)
    assert len(r.ownership) == 361
    assert r.ownership[0] == 0.5


def test_parse_ownership_wrong_count_ignored():
    # Only 10 floats instead of 361
    body = "info move Q16 visits 100 winrate 0.5 ownership " + " ".join(["0.5"] * 10) + "\n"
    r = parse_analysis(body)
    assert r.ownership == []


def test_parse_last_line_wins():
    body = "info move D4 visits 10 winrate 0.4\ninfo move Q16 visits 100 winrate 0.6\n"
    r = parse_analysis(body)
    # Only last line is parsed
    assert any(m.move == "Q16" for m in r.top_moves)
    assert all(m.move != "D4" for m in r.top_moves)
