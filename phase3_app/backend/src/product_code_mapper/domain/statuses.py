from enum import Enum


class MatchStatus(str, Enum):
    AUTO_CODE = "自动落码"
    AUTO_CODE_WITH_DIFFERENCE = "自动落码但有表达差异"
    SUGGESTED_REVIEW = "建议落码待确认"
    MANUAL_REVIEW = "必须人工审核"
    NO_RELIABLE_MATCH = "未找到可靠匹配"
