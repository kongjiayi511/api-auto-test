# -*- coding: utf-8 -*-
"""
pytest 共享夹具（fixture）

【夹具是什么】
  官方翻译叫"夹具"，你可以理解成"用例运行前准备好的东西"。
  比如每个用例都要一个 api 客户端 —— 与其在 5 个用例里各写一遍，
  不如写在 conftest.py 里一次，所有用例按名字取用。

【为什么叫 conftest.py】
  这是 pytest 的约定文件名，放了这个文件，它所在目录及子目录下的
  所有用例都能直接用里面定义的 fixture，不用 import。

【两个关键参数】
  scope="session"  -> 整个测试过程只创建一次（适合"客户端"这种重的对象）
  scope="function" -> 每条用例都新建一次（pytest 的默认值，适合"数据"）
  区别的实际影响：客户端复用连接更快；数据每次新建才不会互相污染。
"""

import pytest

from common.request_client import ApiClient


@pytest.fixture(scope="session")
def api():
    """整个会话共用一个接口客户端（复用连接，比每次新建快）

    base_url 从 config.ini 读，所以 Day3 那个"改配置切环境"的能力
    在这里自动生效 —— 5 条用例不用改一个字就能指向别的环境。
    """
    return ApiClient()


@pytest.fixture()
def new_post_payload():
    """新建文章用的请求体

    注意：这里用函数返回，而不是在外面定义成一个字典常量。
    因为字典是可变对象，如果被某条用例改过，下一条用例会拿到脏数据。
    每次调用都造一个新的，用例之间才真正互不影响。
    """
    return {
        "title": "接口自动化测试",
        "body": "由 pytest 自动提交",
        "userId": 1,
    }
