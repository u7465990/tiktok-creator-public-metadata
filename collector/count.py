"""把页面上的展示型数字转成整数。纯函数，无 I/O。"""
import re
from typing import Optional

_MULT = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
_CN_MULT = {"万": 10_000, "亿": 100_000_000}
_NUM = re.compile(r"^([0-9]+(?:\.[0-9]+)?)\s*([kKmMbB万 亿]?)$")


def parse_count(text) -> Optional[int]:
    """'1.2K' -> 1200；'3.4M' -> 3400000；'12,345' -> 12345；无法解析 -> None。

    绝不返回 0 冒充未知（0 是一个有意义的真实值）。
    """
    if text is None:
        return None
    if isinstance(text, int) and not isinstance(text, bool):
        return text if text >= 0 else None
    if not isinstance(text, str):
        return None

    s = text.strip().replace(",", "").replace("，", "")
    s = re.sub(r"(粉丝|followers?|fans)", "", s, flags=re.I).strip()
    if not s or s in {"-", "—", "N/A", "n/a", "null", "None"}:
        return None

    m = _NUM.match(s)
    if not m:
        return None
    number, suffix = m.group(1), m.group(2)
    try:
        value = float(number)
    except ValueError:
        return None
    if value < 0:
        return None

    if suffix in _CN_MULT:
        return int(round(value * _CN_MULT[suffix]))
    if suffix:
        return int(round(value * _MULT[suffix.lower()]))
    return int(round(value))
