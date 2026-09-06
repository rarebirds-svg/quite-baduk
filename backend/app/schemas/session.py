from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=128)


class AccountPublic(BaseModel):
    provider: str
    email: str | None = None


class SessionPublic(BaseModel):
    id: int
    nickname: str
    # 앱 셸(Capacitor)용 Bearer 토큰. 세션 생성 응답에만 채워진다.
    token: str | None = None
    # 연동된 외부 계정. 없으면 None (순수 닉네임 세션).
    account: AccountPublic | None = None


class NicknameAvailability(BaseModel):
    available: bool
    reason: str | None = None  # "taken" | "invalid"
