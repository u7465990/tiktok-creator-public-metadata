"""语言判定：只用公开文本（当前只有 bio），证据不足返回 und。"""
import re
from typing import Optional, Tuple

# 文字系统 -> 语言（先判断更具体的）
_SCRIPT_RULES = [
    ("ja", re.compile(r"[\u3040-\u30ff]")),   # 假名优先于汉字
    ("ko", re.compile(r"[\uac00-\ud7af]")),
    ("zh", re.compile(r"[\u4e00-\u9fff]")),
    ("ru", re.compile(r"[\u0400-\u04ff]")),
    ("ar", re.compile(r"[\u0600-\u06ff]")),
    ("th", re.compile(r"[\u0e00-\u0e7f]")),
    ("he", re.compile(r"[\u0590-\u05ff]")),
    ("hi", re.compile(r"[\u0900-\u097f]")),
]

# 拉丁字母语言的判别词（尽量选区分度高的，避免 de/que 这类多语言共用词）
_STOPWORDS = {
    "en": {"the", "and", "you", "your", "is", "are", "my", "with", "this",
           "that", "for", "have", "love", "life", "follow", "just"},
    "es": {"el", "los", "las", "por", "para", "con", "mi", "soy", "vida",
           "amor", "pero", "todo", "más", "aquí"},
    "pt": {"os", "as", "com", "para", "meu", "minha", "sou", "vida", "amor",
           "não", "muito", "aqui", "também"},
    "fr": {"les", "des", "avec", "pour", "mon", "ma", "mes", "suis", "vie",
           "amour", "pas", "tout", "ici"},
    "de": {"der", "die", "das", "und", "ein", "eine", "mit", "für", "mein",
           "meine", "bin", "leben", "liebe", "nicht"},
    "it": {"gli", "con", "per", "mio", "mia", "sono", "vita", "amore",
           "non", "tutto", "qui", "anche"},
    "id": {"yang", "dan", "dari", "untuk", "saya", "aku", "ini", "itu",
           "dengan", "tidak", "hidup", "cinta"},
    "vi": {"của", "là", "tôi", "bạn", "không", "một", "những", "cho",
           "với", "yêu", "cuộc"},
    "tr": {"bir", "bu", "için", "ben", "sen", "ile", "çok", "hayat", "aşk"},
    "nl": {"het", "een", "van", "ik", "met", "voor", "niet", "leven", "liefde"},
    "pl": {"nie", "jest", "mój", "moja", "życie", "miłość", "tutaj"},
}


# 强标记词：在目标语言里高频、在其他语言里极少出现。
# 允许"≥3 个词 + 命中 1 个"直接判定，以覆盖 "Living the American Dream" 这类短句；
# 但置信度上限压到 0.5，避免与多信号判定同权。
_STRONG_MARKERS = {
    "en": {"the", "and", "is", "are", "you", "your", "this", "that",
           "with", "have", "my", "was", "were", "don't", "it's"},
}


def detect_language(bio: Optional[str]) -> Tuple[str, float, Optional[dict]]:
    """返回 (language, confidence, evidence)。证据不足时返回 ('und', 低置信, evidence)。"""
    if not bio or not bio.strip():
        return "und", 0.0, None

    text = bio.strip()
    sample = text[:160]
    evidence = {"method": None, "source": "bio", "sample": sample, "notes": None}

    # 1) 文字系统：只要出现足够多的非拉丁字符，基本可定
    for code, pattern in _SCRIPT_RULES:
        hits = len(pattern.findall(text))
        if hits >= 2:
            evidence["method"] = "script-detection"
            evidence["notes"] = f"{code} 字符数 {hits}"
            confidence = min(0.95, 0.6 + 0.05 * hits)
            return code, round(confidence, 2), evidence

    # 2) 强标记词：这类词几乎只出现在单一语言里，允许单次命中即判定
    tokens = re.findall(r"[a-zA-ZÀ-ÿ']+", text.lower())
    if len(tokens) >= 3:
        for code, markers in _STRONG_MARKERS.items():
            hits = sorted(set(tokens) & markers)
            if hits:
                evidence["method"] = "strong-marker"
                evidence["notes"] = f"{code} 强标记词 {hits}（tokens={len(tokens)}）"
                return code, 0.5, evidence

    # 3) 拉丁字母：停用词投票（弱信号，需要多次命中互相印证）
    words = set(tokens)
    scores = {code: len(words & bag) for code, bag in _STOPWORDS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_code, best = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0

    evidence["method"] = "stopword-vote"
    evidence["notes"] = f"top={best_code}:{best}, second={second}, tokens={len(words)}"

    # 至少命中 2 个且明显领先，否则不猜
    if best >= 2 and best >= second + 1:
        confidence = min(0.9, 0.35 + 0.1 * best)
        evidence["notes"] += "（判定为拉丁语言）"
        return best_code, round(confidence, 2), evidence

    evidence["notes"] += "（证据不足，降级 und）"
    return "und", 0.2, evidence
