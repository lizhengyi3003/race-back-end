# -*- coding: utf-8 -*-
"""验证评分引擎对枚举档位/数值方向的打分（用导入后的 DB 数据）。"""
import sys
sys.path.insert(0, r"e:\Project\Web\race\back-end")

from app.db.session import SessionLocal
from app.models.indicator import IndicatorConfig
from app.ml.expert_engine import _score_enum, _score_value, _score_bool

CASES = [
    # (指标名, 值) 期望方向：好的应高分
    ("近三年自然灾害受灾程度", "无"),
    ("近三年自然灾害受灾程度", "重"),
    ("寒地低温冻害风险等级", "低"),
    ("寒地低温冻害风险等级", "高"),
    ("经营者不良嗜好情况", "无"),
    ("经营者不良嗜好情况", "明显"),
    ("社区/村镇口碑", "好"),
    ("社区/村镇口碑", "差"),
    ("绿色食品认证情况", "已认证"),
    ("绿色食品认证情况", "无"),
    ("银行信贷履约记录", "无逾期"),
    ("银行信贷履约记录", "有逾期"),
    ("银行信贷履约记录", "逾期已结清"),
    ("疫病防控体系", "完善"),
    ("疫病防控体系", "缺失"),
]

with SessionLocal() as db:
    print("=== 枚举档位方向（期望：好>差）===")
    for name, val in CASES:
        ind = db.query(IndicatorConfig).filter(IndicatorConfig.name == name).first()
        if not ind:
            print(f"{name}: 未找到!"); continue
        s = _score_enum(val, ind)
        print(f"{name} = {val} -> {s}")

    print("\n=== 数值方向（期望：风险越高分越低）===")
    for name in ["经营者个人经营性贷款余额", "产成品库存周转天数"]:
        ind = db.query(IndicatorConfig).filter(IndicatorConfig.name == name).first()
        s_lo, s_hi = _score_value(5, ind), _score_value(95, ind)
        print(f"{name}: 值5 -> {s_lo}, 值95 -> {s_hi}  (lower_better={ind.scoring_config})")
