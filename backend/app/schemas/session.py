from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=128)


class SessionPublic(BaseModel):
    id: int
    nickname: str


class NicknameAvailability(BaseModel):
    available: bool
    reason: str | None = None  # "taken" | "invalid"
