# -*- coding: utf-8 -*-
"""
posts 资源接口测试用例

【用例结构：准备 -> 执行 -> 断言】
  准备(Arrange)：取客户端、造请求体
  执行(Act)    ：发请求
  断言(Assert) ：判断结果对不对 —— 这一步才是"测试"

  只发请求不断言的脚本，只能算"调接口看结果"，不能算自动化测试。

【为什么用类把用例分组】
  一个资源（posts）的用例放一个类，跑失败时报告里一眼看出是哪块坏了。
  类名必须以 Test 开头，这是 pytest.ini 里 python_classes 定的规矩。

【三条原则】
  1. 用例之间不能有先后依赖 —— 单独跑第 3 条也必须能过
  2. 一条用例只验证一件事 —— 失败了你才知道坏在哪
  3. 不要写 print —— 断言失败时 pytest 会自己告诉你期望值和实际值
"""

import pytest


class TestPosts:
    """posts 资源的接口用例"""

    # ---------- 用例 1：查一条存在的 ----------
    @pytest.mark.smoke
    def test_get_single_post(self, api):
        """查 id=1 的文章：应返回 200，且内容确实是那一条"""
        # 执行
        resp = api.get("/posts/1")

        # 断言：先判状态码，再判内容
        # 顺序很重要 —— 状态码不对时，后面解析内容没意义
        assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}"

        data = resp.json()
        # 用 .get() 而不是 data["id"]：
        #   若字段不存在，data["id"] 抛 KeyError（报错信息很难懂）
        #   data.get("id") 返回 None，断言失败信息清晰
        assert data.get("id") == 1, f"id 应为 1，实际 {data.get('id')}"

        # 逐个检查关键字段有没有丢
        for field in ("title", "body", "userId"):
            assert field in data, f"返回体缺少字段：{field}"

    # ---------- 用例 2：查列表 + 查询参数 ----------
    def test_get_posts_filtered_by_user(self, api):
        """按 userId=1 过滤：应返回 200，且正好 10 条、每条都属于该用户"""
        resp = api.get("/posts", params={"userId": 1})

        assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}"

        data = resp.json()
        # 先确认拿到的确实是列表，再做长度判断
        # 不加这句的话，如果返回的是字典，len() 会算出"键的个数"，看起来是对的但其实错了
        assert isinstance(data, list), f"期望列表，实际 {type(data).__name__}"
        assert len(data) == 10, f"userId=1 应有 10 条，实际 {len(data)}"

        # all(...) 检查每一条都符合条件 —— 只看第一条是不够的
        assert all(item["userId"] == 1 for item in data), "存在 userId 不为 1 的数据"

    # ---------- 用例 3：新建 ----------
    @pytest.mark.smoke
    def test_create_post(self, api, new_post_payload):
        """新建文章：应返回 201（不是 200！），且回显提交的内容"""
        resp = api.post("/posts", json=new_post_payload)

        # 新建成功是 201 Created，这是 HTTP 规范定的
        assert resp.status_code == 201, f"期望 201，实际 {resp.status_code}"

        data = resp.json()
        # 检查"我提交什么，它就返回什么"——这叫回显校验
        assert data.get("title") == new_post_payload["title"], "title 没有正确回显"
        assert data.get("userId") == new_post_payload["userId"], "userId 没有正确回显"
        # 服务器应该分配一个新 id
        assert data.get("id") is not None, "新建后没有返回 id"

    # ---------- 用例 4：查一条不存在的（异常场景）----------
    @pytest.mark.negative
    def test_get_nonexistent_post_returns_404(self, api):
        """查不存在的资源：应返回 404

        这条是"负向用例"——验证系统在该报错的时候确实报错了。
        只会写正向用例的人，是初级测试。
        """
        resp = api.get("/posts/999999")

        assert resp.status_code == 404, f"期望 404，实际 {resp.status_code}"

    # ---------- 用例 5：删除 ----------
    def test_delete_post(self, api):
        """删除文章：应返回 200，响应体不含业务数据"""
        resp = api.delete("/posts/1")

        assert resp.status_code == 200, f"期望 200，实际 {resp.status_code}"

        # 删除成功常见约定是返回空对象 {}，但也可能返回空 body。
        # 直接 resp.json() 在"空 body"时会抛异常，用 safe_json 兜底。
        assert api.safe_json(resp, {}) == {}, f"删除后应返回空对象，实际 {api.safe_json(resp)}"
