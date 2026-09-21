"""东八区（UTC+8）自然日归日工具。

业务约定：湿度上限账按「东八区自然日」归日，与服务器本地时区无关。
这里使用固定的 UTC+8 偏移（而非 Asia/Shanghai 的历书时区），
保证任意历史/未来时刻都严格按 UTC+8 切日。
"""
from datetime import timedelta, timezone as dt_timezone

from django.utils import timezone

# 固定 UTC+8 偏移的东八区时区
EAST8 = dt_timezone(timedelta(hours=8), name="UTC+8")


def east8_date(dt):
    """返回某个时刻在东八区自然日下的日期（date）。

    - aware 时间：先换算到 UTC+8 再取日期；
    - naive 时间：视为东八区墙钟时间，直接取日期。
    """
    if dt is None:
        return None
    if timezone.is_naive(dt):
        return dt.date()
    return dt.astimezone(EAST8).date()


def east8_today():
    """当前时刻的东八区自然日日期。"""
    return timezone.now().astimezone(EAST8).date()
