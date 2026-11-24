# -*- coding: utf-8 -*-
"""
Excel 用例读取层

职责只有一件事：把 data/test_cases.xlsx 里的每一行，变成用例代码能直接用的数据。

【为什么单独抽一层】
  如果直接在用例文件里写 openpyxl.load_workbook(...)，一旦想把用例来源
  从 Excel 换成 YAML、数据库或接口，用例代码就得跟着改。
  抽成这一层之后，用例只认 load_cases() 返回的字典结构，来源随便换。

【为什么在"收集阶段"读，而不是每条用例自己去读】
  pytest 需要提前知道有多少条用例（才能排版号、算进度）。
  所以在模块导入时就读完，用 parametrize 一次性生成所有用例。
  代价是：改完 Excel 必须重新执行 pytest，热更新做不到 —— 这是可接受的。
"""

import json
import os

from openpyxl import load_workbook

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(BASE_DIR, "data", "test_cases.xlsx")

SHEET_NAME = "接口用例"


def _split(text):
    """把 "a,b,c" 拆成 ["a","b","c"]，自动去空格、去空项"""
    if text is None:
        return []
    return [x.strip() for x in str(text).split(",") if x.strip()]


def _parse_params(text):
    """把 "userId=1&_limit=5" 解析成 {"userId": 1, "_limit": 5}

    纯数字的值转成 int：不是必须，但让请求参数的类型和真实接口一致，
    避免以后接真实业务接口时因为 "1" 和 1 的差异踩坑。
    """
    if not text:
        return None
    result = {}
    for pair in str(text).split("&"):
        if not pair.strip():
            continue
        if "=" not in pair:
            raise ValueError(f"查询参数格式不对，应为 k=v：{pair}")
        k, v = pair.split("=", 1)
        k, v = k.strip(), v.strip()
        result[k] = int(v) if v.lstrip("-").isdigit() else v
    return result


def _parse_body(text):
    """请求体必须是合法 JSON。这里是唯一允许直接抛异常的地方 ——
    用例表写错了应该在收集阶段就报错，而不是跑到一半才崩。"""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"请求体不是合法 JSON：{text!r}，错误：{e}") from e


def _parse_expected_values(text):
    """把 "id=1,title=局部更新" 解析成 {"id": "1", "title": "局部更新"}"""
    if not text:
        return {}
    result = {}
    for pair in str(text).split(","):
        if not pair.strip():
            continue
        if "=" not in pair:
            raise ValueError(f"期望字段值格式不对，应为 k=v：{pair}")
        k, v = pair.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def load_cases(path=None, sheet=None):
    """读取用例表，返回用例字典列表（已过滤掉「启用」不为 Y 的行）

    返回结构：
        {
          "case_id": "TC-001",
          "name": "查询单条文章-存在",
          "kind": "正向",
          "env": "main",
          "method": "GET",
          "path": "/posts/1",
          "params": {...} 或 None,
          "body": {...} 或 None,
          "expect_status": 200,
          "expect_fields": ["id", "title"],
          "expect_values": {"id": "1"},
          "expect_count": None 或 int,
          "note": "..."
        }
    """
    path = path or DEFAULT_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到用例表：{path}")

    wb = load_workbook(path, data_only=True)
    ws = wb[sheet or SHEET_NAME]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    cases = []

    for raw in rows[1:]:
        row = dict(zip(header, raw))

        # 整行空白直接跳过（Excel 底部经常留一堆空行）
        if not any(v not in (None, "") for v in raw):
            continue

        # 只跑「启用」为 Y 的用例
        if str(row.get("启用") or "").strip().upper() != "Y":
            continue

        expect_count = row.get("期望条数")
        cases.append(
            {
                "case_id": str(row.get("用例ID") or "").strip(),
                "name": str(row.get("用例名称") or "").strip(),
                "kind": str(row.get("场景类型") or "").strip(),
                "env": str(row.get("环境") or "main").strip(),
                "method": str(row.get("方法") or "GET").strip().upper(),
                "path": str(row.get("路径") or "").strip(),
                "params": _parse_params(row.get("查询参数")),
                "body": _parse_body(row.get("请求体")),
                "expect_status": int(row.get("期望状态码")),
                "expect_fields": _split(row.get("期望字段")),
                "expect_values": _parse_expected_values(row.get("期望字段值")),
                "expect_count": int(expect_count) if expect_count not in (None, "") else None,
                "note": str(row.get("备注") or "").strip(),
            }
        )

    return cases


if __name__ == "__main__":
    # 单独运行可以检查用例表读得对不对
    all_cases = load_cases()
    print(f"共读取 {len(all_cases)} 条启用用例\n")
    for c in all_cases:
        print(f"{c['case_id']} [{c['kind']}] {c['method']:6} {c['path']:18} 期望 {c['expect_status']}  {c['name']}")
