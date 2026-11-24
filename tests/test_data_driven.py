# -*- coding: utf-8 -*-
"""
数据驱动用例：用例内容全部来自 data/test_cases.xlsx

【和 test_posts.py 的区别】
  test_posts.py：用例写在代码里 —— 加一条用例要写一个函数、敲一遍 pytest
  本文件      ：用例写在 Excel 里 —— 加一行数据就多一条用例，代码一个字不改

【为什么这件事重要】
  接口测试的特点是"用例多、步骤雷同、判断标准固定"，非常适合外置成数据。
  一个业务模块几十条接口，如果每条都写一个函数，维护成本会压过收益。
  外置之后，测试人员改 Excel 不需要懂 Python，改完直接跑。

【代价也要清楚】
  Excel 表达不了复杂逻辑。凡是要"先造数据再用"、"上一步的返回值喂给下一步"
  的链路用例，写成代码更清楚。所以本项目是两种方式并存：
  简单用例走 Excel，复杂用例写代码 —— 真实项目里也是这么分工的。
"""

import pytest

from common.excel_reader import load_cases

# 在模块导入时读一次（pytest 收集用例时需要提前知道总条数）
CASES = load_cases()


def _params():
    """把用例字典包装成 pytest 参数

    id 用"编号-名称"，报告里一眼能定位到 Excel 的哪一行。

    顺便按「场景类型」自动挂标记：
      负向用例挂 negative —— 这样可以 python -m pytest -m negative
      只跑异常场景，做一轮"抗压检查"，不用等全量跑完。
    """
    result = []
    for c in CASES:
        marks = [pytest.mark.negative] if c["kind"] == "负向" else []
        result.append(pytest.param(c, id=f"{c['case_id']}-{c['name']}", marks=marks))
    return result


class TestDataDriven:
    """按 Excel 用例表逐条执行"""

    @pytest.mark.parametrize("case", _params())
    def test_api_case(self, api, api_alt, case):
        """通用执行器：所有 Excel 用例都走这一条代码

        注意入参同时请求了 api 和 api_alt 两个夹具 —— pytest 只会在
        用例真正用到时才实例化，这里按 case["env"] 二选一。
        """
        # ---------- 1. 选环境 ----------
        client = api if case["env"] == "main" else api_alt

        # 组装出请求参数，None 的一律不传，避免 requests 把 None 当成实际参数发出去
        kwargs = {}
        if case["params"]:
            kwargs["params"] = case["params"]
        if case["body"] is not None:
            kwargs["json"] = case["body"]

        # ---------- 2. 执行 ----------
        resp = client.request(case["method"], case["path"], **kwargs)

        # ---------- 3. 断言 ----------
        # 3.1 状态码：永远是第一个断言
        assert resp.status_code == case["expect_status"], (
            f"[{case['case_id']}] {case['name']} 状态码不符："
            f"期望 {case['expect_status']}，实际 {resp.status_code}。"
            f"请求 {case['method']} {case['path']}，备注：{case['note']}"
        )

        # 3.2 只有成功响应才检查响应体内容。
        #     4xx/5xx 的响应体格式不固定（可能 HTML、可能空、可能 JSON），
        #     硬去解析只会得到一堆和真正问题无关的报错。
        if case["expect_status"] >= 400:
            return

        data = client.safe_json(resp)

        # 3.3 返回条数（针对列表接口）
        if case["expect_count"] is not None:
            assert isinstance(data, list), (
                f"[{case['case_id']}] 期望返回列表，实际是 {type(data).__name__}"
            )
            assert len(data) == case["expect_count"], (
                f"[{case['case_id']}] 返回条数不符："
                f"期望 {case['expect_count']}，实际 {len(data)}"
            )

        # 3.4 必需字段是否存在
        if isinstance(data, dict):
            for field in case["expect_fields"]:
                assert field in data, (
                    f"[{case['case_id']}] 响应体缺少字段 {field}，实际字段：{list(data.keys())}"
                )

            # 3.5 字段值是否正确（统一转成字符串比较，避免 1 和 "1" 的误判）
            for field, expect in case["expect_values"].items():
                actual = data.get(field)
                assert str(actual) == expect, (
                    f"[{case['case_id']}] 字段 {field} 的值不符："
                    f"期望 {expect}，实际 {actual}"
                )


class TestCaseTable:
    """对用例表本身的校验 —— 防止"脏数据"让用例静默失效"""

    def test_case_ids_are_unique(self):
        """用例编号不能重复：重复的话报告里两条用例同名，排查时找不到是哪条"""
        ids = [c["case_id"] for c in CASES]
        duplicated = {i for i in ids if ids.count(i) > 1}
        assert not duplicated, f"用例编号重复：{duplicated}"

    def test_all_cases_have_required_fields(self):
        """每条用例都必须有编号、名称、路径、期望状态码

        漏填期望状态码时，int(None) 会直接报错，但报错位置在读取层，
        看不出是哪一行的问题。这条用例让问题在用例层面暴露出来。
        """
        for c in CASES:
            assert c["case_id"], f"存在没有编号的用例：{c}"
            assert c["name"], f"用例 {c['case_id']} 没有名称"
            assert c["path"].startswith("/"), f"用例 {c['case_id']} 路径必须以 / 开头"
            assert c["expect_status"] > 0, f"用例 {c['case_id']} 期望状态码不合法"

    def test_negative_cases_have_4xx_or_5xx(self):
        """标为负向的用例，期望状态码必须是 4xx/5xx

        这条能抓出一类隐蔽错误：把一条本该报错的用例写成了期望 200，
        等于把 bug 当成正确行为固定下来 —— 这比漏测更危险。
        """
        for c in CASES:
            if c["kind"] == "负向":
                assert c["expect_status"] >= 400, (
                    f"负向用例 {c['case_id']} 的期望状态码是 {c['expect_status']}，应为 4xx/5xx"
                )
