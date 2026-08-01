"""认证相关请求/响应"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    real_name: str
    role: str
    status: int
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut
