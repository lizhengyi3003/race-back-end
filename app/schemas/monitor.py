"""系统监控：服务器状态 / 数据库状态 / 健康检查"""

from datetime import datetime

from pydantic import BaseModel


class MemoryInfo(BaseModel):
    total: float  # MB
    used: float
    free: float
    percent: float


class DiskInfo(BaseModel):
    total: float  # GB
    used: float
    free: float
    percent: float


class CpuInfo(BaseModel):
    percent: float
    cores: int
    freq: float  # MHz


class ServerStatus(BaseModel):
    hostname: str
    platform: str
    pythonVersion: str
    uptimeSeconds: float
    bootTime: datetime | None = None
    cpu: CpuInfo
    memory: MemoryInfo
    disk: DiskInfo
    processCpu: float
    processMemory: float  # MB
    threads: int


class TableInfo(BaseModel):
    name: str
    rows: int
    sizeMb: float


class DatabaseStatus(BaseModel):
    connected: bool
    dialect: str
    tables: list[TableInfo]
    totalSizeMb: float


class HealthStatus(BaseModel):
    status: str  # healthy / degraded / down
    service: str
    database: str
    modelExists: bool
    modelVersion: str | None = None
    timestamp: datetime
