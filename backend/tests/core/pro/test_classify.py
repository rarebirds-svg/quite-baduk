# classify_collection 단위 테스트.
from app.core.pro.classify import classify_collection


def test_world_events():
    assert classify_collection("10th Chunlan Cup Final") == "world"
    assert classify_collection("30th LG Cup Final") == "world"
    assert classify_collection("Samsung Cup") == "world"


def test_masterpiece_default():
    assert classify_collection("32nd Agon-Kiriyama Cup") == "masterpiece"
    assert classify_collection("Castle Game") == "masterpiece"
    assert classify_collection(None) == "masterpiece"
