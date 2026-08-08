"""清洗规则表达式引擎：安全解析并执行 mappings.py 中的 clean_rule。

支持的语法（受限白名单，AST 校验，防注入）：
- {field}            引用数据源字段（返回 pandas Series，缺失为 NaN）
- 数字字面量、四则运算 + - * / 、取负
- 比较 < <= > >= == != 与逻辑 and/or/not（返回布尔 Series）
- 函数：
  clip(x, lo, hi)     截断到 [lo, hi]
  sum(a, b, ...)      加总（每个缺失按 0 处理）
  div(x, n)           x / n
  map(x, {k:v,...})   枚举映射（字典字面量；缺失保持 NaN）
  coalesce(a, b, ...) 依次取首个非空
  fill(x, y)          x 缺失时用 y
  mask(x, cond)       cond 为真处取 x，否则 NaN
  int(x)              取整
  ifnull(x, v)        x 为 NaN 用 v
"""

from __future__ import annotations

import ast
import operator
from typing import Any

import pandas as pd

# ---------- 白名单函数 ----------
_FUNCS: dict[str, Any] = {}


def _register(fn):
    _FUNCS[fn.__name__] = fn
    return fn


@_register
def clip(x, lo, hi):
    return x.clip(float(lo), float(hi))


@_register
def sum(*xs):
    out = None
    for x in xs:
        s = x.fillna(0) if isinstance(x, pd.Series) else x
        out = s if out is None else out + s
    return out


@_register
def div(x, n):
    return x / n  # n 可为标量或 Series


@_register
def map(x, mapping):
    m = {int(k): v for k, v in mapping.items()}
    return x.map(m)


@_register
def coalesce(*xs):
    out = xs[0]
    for x in xs[1:]:
        out = out.fillna(x)
    return out


@_register
def fill(x, y):
    return x.fillna(y)


@_register
def mask(x, cond):
    return x.where(cond)


@_register
def int_(x):
    return x.astype("float").round()


@_register
def ifnull(x, v):
    return x.fillna(v)


_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.And: operator.and_,
    ast.Or: operator.or_,
    ast.Not: operator.not_,
}


class _RuleError(ValueError):
    pass


def _eval_node(node: ast.AST, fields: dict[str, pd.Series]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        # 字段引用：{field} 已转成 Name
        if node.id in fields:
            return fields[node.id]
        raise _RuleError(f"未定义字段: {node.id}")
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left, fields), _eval_node(node.right, fields))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand, fields))
    if isinstance(node, ast.BoolOp):
        vals = [_eval_node(v, fields) for v in node.values]
        return _OPS[type(node.op)](*vals) if len(vals) > 1 else vals[0]
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, fields)
        results = []
        for op, comp in zip(node.ops, node.comparators):
            right = _eval_node(comp, fields)
            results.append(_OPS[type(op)](left, right))
            left = right
        if len(results) == 1:
            return results[0]
        out = results[0]
        for r in results[1:]:
            out = (out & r) if isinstance(out, pd.Series) else bool(out and r)
        return out
    if isinstance(node, ast.Call):
        fn = node.func
        if not isinstance(fn, ast.Name) or fn.id not in _FUNCS:
            raise _RuleError(f"不允许的函数: {getattr(fn, 'id', fn)}")
        args = [_eval_node(a, fields) for a in node.args]
        kwargs = {k.arg: _eval_node(k.value, fields) for k in node.keywords}
        return _FUNCS[fn.id](*args, **kwargs)
    if isinstance(node, ast.Dict):
        return {_eval_node(k, fields): _eval_node(v, fields) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.IfExp):
        return _eval_node(node.body, fields) if _eval_node(node.test, fields) else _eval_node(node.orelse, fields)
    raise _RuleError(f"不支持的语法节点: {type(node).__name__}")


def _rewrite_field_refs(expr: str) -> str:
    """把 {field} 引用转成 Name 节点（field 经 ast.Name 校验）。"""
    import re

    def repl(m):
        name = m.group(1)
        # 字段名以字母/下划线开头，后续字母数字下划线（排除 map 的 {1:1} 字典）
        return name

    return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, expr)


def eval_rule(rule: str, df: pd.DataFrame) -> pd.Series:
    """执行清洗规则，返回 Series（缺失为 NaN）。"""
    expr = _rewrite_field_refs(rule)
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise _RuleError(f"规则语法错误 [{rule}]: {e}") from e
    fields = {c: df[c] for c in df.columns}
    result = _eval_node(tree.body, fields)
    if isinstance(result, pd.Series):
        return result.astype("float64")
    return pd.Series(float(result), index=df.index)


if __name__ == "__main__":
    # 自测
    d = pd.DataFrame({"a1006": [2005, 2013, 1999], "bi3006": [50000, None, 20000], "e1014": [1, 2, None]})
    print(eval_rule("clip(2015-{a1006},0,60)", d).tolist())
    print(eval_rule("div(sum({bi3006},{bi3006}),10000)", d).tolist())
    print(eval_rule("map({e1014},{1:1,2:0})", d).tolist())
    print(eval_rule("coalesce({bi3006},0)", d).tolist())
