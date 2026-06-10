from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=128)


class SessionPublic(BaseModel):
    id: int
    nickname: str
    # 앱 셸(Capacitor)용 Bearer 토큰. 세션 생성 응답에만 채워진다.
    token: str | None = None


class NicknameAvailability(BaseModel):
    available: bool
    reason: str | None = None  # "taken" | "invalid"
