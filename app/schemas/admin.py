"""管理平台：用户管理 / API 日志 / 系统概览"""

from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    realName: str = ""
    role: str = "analyst"  # admin / analyst


class UserUpdate(BaseModel):
    realName: str | None = None
    role: str | None = None
    status: int | None = None


class ResetPasswordRequest(BaseModel):
    newPassword: str


class ApiLogOut(BaseModel):
    id: int
    method: str
    path: str
    statusCode: int
    durationMs: float
    clientIp: str | None = None
    username: str | None = None
    reqBody: str | None = None
    respPreview: str | None = None
    createdAt: datetime | None = None


class ApiSpecItem(BaseModel):
    method: str
    path: str
    summary: str
    tags: list[str]
    authRequired: bool = False
    parameters: list[dict] = []
    requestBodyExample: str | None = None


class SystemOverview(BaseModel):
    users: int
    records: int
    models: int
    apiLogs: int
    apiLogsToday: int
    database: str
    version: str
    serverTime: datetime
