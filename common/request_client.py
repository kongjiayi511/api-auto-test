# -*- coding: utf-8 -*-
"""
请求层（核心）
所有接口请求都从这里走，统一做三件事：
  1. 自动拼上 config.ini 里的 base_url
  2. 每次请求/响应都记日志
  3. 统一设置超时

这样上层的测试代码只关心"调哪个接口、传什么参数"，
不用管地址前缀、日志、超时这些琐事 —— 这就是"封装"的意义。

切换测试环境只需改 config.ini 的 base_url，用例代码零改动。
"""

import requests

from common.config_reader import BASE_URL, TIMEOUT
from common.logger import logger


class ApiClient:
    """一个极简但好用的接口客户端"""

    def __init__(self, base_url=None):
        # 允许外部传入，不传就用配置文件里的
        self.base_url = (base_url or BASE_URL).rstrip("/")
        # 用 Session 复用连接，比每次新建连接快，还能统一带请求头
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _send(self, method, path, **kwargs):
        """
        内部统一处理：拼地址 -> 发请求 -> 记日志
        method: GET/POST/PUT/DELETE...
        path:   '/posts/1' 这种相对路径
        """
        url = self.base_url + path
        kwargs.setdefault("timeout", TIMEOUT)

        logger.info(f"--> 请求 {method} {url}" + (f" | 参数={kwargs.get('params') or kwargs.get('json')}" if (kwargs.get('params') or kwargs.get('json')) else ""))

        try:
            resp = self.session.request(method, url, **kwargs)
        except requests.exceptions.RequestException as e:
            # 网络层异常（超时、连不上）也要记下来
            logger.error(f"<-- 请求异常 {method} {url} | {e}")
            raise

        logger.info(
            f"<-- 响应 {resp.status_code} {method} {url} "
            f"| 耗时 {resp.elapsed.total_seconds():.3f}s"
        )
        return resp

    # ---------- 对外提供的便捷方法 ----------
    def request(self, method, path, **kwargs):
        """通用入口：方法名由调用方给（数据驱动就靠它）

        Excel 里那一列"方法"填 POST 还是 GET，最终都走到这里，
        不用为每种方法写一堆 if/else。
        """
        return self._send(method.upper(), path, **kwargs)

    def get(self, path, **kwargs):
        return self._send("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self._send("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self._send("PUT", path, **kwargs)

    def patch(self, path, **kwargs):
        # PATCH 是"局部更新"：只提交要改的字段，其余保持原样
        # 和 PUT 的区别经常被面试问到，别混
        return self._send("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self._send("DELETE", path, **kwargs)

    # ---------- 响应解析 ----------
    @staticmethod
    def safe_json(resp, default=None):
        """安全解析 JSON：解析不了就返回 default，绝不抛异常

        为什么需要它：
          不能假设"响应体一定是 JSON"。
          同一个 404，业务后端可能返回 {"detail": "Not Found"}，
          而网关/负载均衡通常返回一整页 HTML（<html><head>...）。
          这时候 resp.json() 会抛 JSONDecodeError，
          一条本身就"预期失败"的用例反而把整个测试进程带崩。

        这也顺便成了一个判断依据：
          - 响应体是 JSON  -> 请求进到业务层了，是资源本身找不到
          - 响应体是 HTML  -> 请求被网关拦住了，多为路由/发布问题
        """
        try:
            return resp.json()
        except ValueError:
            return default
