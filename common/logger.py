# -*- coding: utf-8 -*-
"""
日志模块
统一用 logging 记录，同时输出到【控制台】和【文件】。
好处：跑完测试后，logs/test.log 里有完整记录，出问题能回溯。
"""

import logging
import os

from common.config_reader import LOG_LEVEL, LOG_FILE


def get_logger(name="api-test"):
    """获取一个 logger，重复调用不会重复添加 handler"""
    logger = logging.getLogger(name)

    # 如果已经配置过，直接返回，避免日志重复打印
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # 统一的日志格式：时间 | 级别 | 模块 | 消息
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1) 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # 2) 文件输出（目录不存在就创建）
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


# 默认 logger，其他模块直接 from common.logger import logger
logger = get_logger()
