# datetime을 UTC 'Z' ISO8601로 직렬화하는 Pydantic 공용 타입 — 프론트 로컬 오해석 방지
import datetime as dt
from typing import Annotated

from pydantic import PlainSerializer


def utc_iso(value: dt.datetime) -> str:
    # DB의 naive 값은 UTC로 간주하고, tz-aware는 UTC로 변환한 뒤 'Z'로 표기한다.
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


# 검증(파싱)은 기본 datetime과 동일, JSON 직렬화만 UTC 'Z'로 정규화한다.
UtcDatetime = Annotated[
    dt.datetime, PlainSerializer(utc_iso, return_type=str, when_used="json")
]
