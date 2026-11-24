# -*- coding: utf-8 -*-
"""
配置读取模块
把 config.ini 的内容读进来，供其他模块使用。
好处：以后想换环境，只改 config.ini，不改任何 .py 代码。
"""

import configparser
import os

# 定位到项目根目录（config.ini 在 common 的上一级）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")


def _load():
    """读取配置文件，返回 configparser 对象"""
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"找不到配置文件：{CONFIG_PATH}")
    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding="utf-8")
    return config


_config = _load()


# 对外暴露的配置值，其他模块直接 from common.config import BASE_URL 即可
BASE_URL = _config["server"]["base_url"].strip()
TIMEOUT = _config["server"].getint("timeout")
LOG_LEVEL = _config["log"]["level"].strip().upper()
LOG_FILE = os.path.join(BASE_DIR, _config["log"]["file"].strip())


if __name__ == "__main__":
    # 单独运行本文件可以检查配置读得对不对
    print("BASE_URL :", BASE_URL)
    print("TIMEOUT  :", TIMEOUT, type(TIMEOUT).__name__)
    print("LOG_LEVEL:", LOG_LEVEL)
    print("LOG_FILE :", LOG_FILE)
