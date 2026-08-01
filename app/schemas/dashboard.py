"""数据看板统计"""

from pydantic import BaseModel


class DashboardStats(BaseModel):
    totalAssess: int
    avgScore: float
    highRiskRate: float  # 高风险占比 %
    passRate: float  # 授信通过率（低+中风险占比）%
    lowCount: int
    midCount: int
    highCount: int


class IndustryItem(BaseModel):
    name: str
    value: int
    risk: str


class ScoreDistItem(BaseModel):
    range: str
    count: int


class TrendItem(BaseModel):
    date: str
    count: int
    avgScore: float
