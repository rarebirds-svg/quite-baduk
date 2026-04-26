"""Cover schema definitions in app.schemas.ws — they're imported at runtime
but never round-tripped through Pydantic in API tests, so without these
their declarations register 0% coverage."""
from __future__ import annotations

from app.schemas.ws import (
    WSAIMoveOut,
    WSErrorOut,
    WSGameOverOut,
    WSMoveIn,
    WSPassIn,
    WSStateOut,
    WSUndoIn,
)


def test_ws_move_in_parses_coord() -> None:
    msg = WSMoveIn(coord="Q16")
    assert msg.type == "move"
    assert msg.coord == "Q16"


def test_ws_pass_in_default_type() -> None:
    msg = WSPassIn()
    assert msg.type == "pass"


def test_ws_undo_in_default_steps() -> None:
    msg = WSUndoIn()
    assert msg.type == "undo"
    assert msg.steps == 2

    custom = WSUndoIn(steps=4)
    assert custom.steps == 4


def test_ws_state_out_includes_captures_dict() -> None:
    msg = WSStateOut(
        board="." * 81,
        board_size=9,
        to_move="B",
        move_count=0,
        captures={"B": 0, "W": 0},
    )
    assert msg.type == "state"
    assert msg.board_size == 9
    assert msg.captures == {"B": 0, "W": 0}


def test_ws_ai_move_out_round_trip() -> None:
    msg = WSAIMoveOut(coord="D4", captures=2)
    dumped = msg.model_dump()
    assert dumped == {"type": "ai_move", "coord": "D4", "captures": 2}


def test_ws_game_over_out_with_winner() -> None:
    msg = WSGameOverOut(result="B+R", winner="user")
    assert msg.type == "game_over"
    assert msg.result == "B+R"


def test_ws_error_out_optional_detail() -> None:
    msg = WSErrorOut(code="OCCUPIED")
    assert msg.detail is None

    with_detail = WSErrorOut(code="ILLEGAL_KO", detail="repeated position")
    assert with_detail.detail == "repeated position"
