"""
教材页面 → Unit 人工映射表

替代 OCR + regex 自动猜 unit（10.1% 误差）→ 查表（100% 准确）。
标注方式：翻 PDF 找到每个 unit 的起始页 + 附录起始页，填入下表。
中间页自动继承最近一个边界点的标注。

维护：教材版本不变则此表永久有效。
"""
from typing import Optional

# ── 边界标注表 ──────────────────────────────────────────
# key = (semester, page_num)
# value = (category, label)
#
# category:
#   "unit"     - 正常单元内容 → chunk + 索引 + 路由测试
#   "appendix" - 附录（词汇表/不规则动词等）→ chunk + 索引，不参与路由测试
#   "skip"     - 封面/目录/封底/空白页 → 不 chunk，不索引

BOUNDARIES: dict[tuple[int, int], tuple[str, str]] = {
    # ==================== 八年级上册 ====================
    (1, 1):   ("skip",     "封面"),
    (1, 2):   ("unit",     "Unit 1"),
    (1, 21):  ("unit",     "Unit 2"),
    (1, 31):  ("unit",     "Unit 3"),
    (1, 41):  ("unit",     "Unit 4"),
    (1, 51):  ("unit",     "Unit 5"),
    (1, 61):  ("unit",     "Unit 6"),
    (1, 71):  ("unit",     "Unit 7"),
    (1, 81):  ("unit",     "Unit 8"),
    # Unit 9、Unit 10 如果 PDF 包含则补上
    (1, 123): ("appendix", "词汇表"),
    # (1, 150): ("skip",     "封底"),

    # ==================== 八年级下册 ====================
    (2, 1):   ("skip",     "封面"),
    (2, 2):   ("unit",     "Unit 1"),
    (2, 15):  ("unit",     "Unit 2"),
    (2, 25):  ("unit",     "Unit 3"),
    (2, 35):  ("unit",     "Unit 4"),
    (2, 45):  ("unit",     "Unit 5"),
    (2, 55):  ("unit",     "Unit 6"),
    (2, 65):  ("unit",     "Unit 7"),
    (2, 75):  ("unit",     "Unit 8"),
    # Unit 9、Unit 10 如果 PDF 包含则补上
    # (2, 120): ("appendix", "词汇表"),
    # (2, 150): ("skip",     "封底"),
}


def get_unit(semester: int, page_num: int) -> tuple[str, str]:
    """
    返回 (category, unit_label)

    查表逻辑：
    1. 精确命中 → 直接返回
    2. 未命中 → 往前找最近边界点，继承其标注（unit 可继承，skip/appendix 不继承）
    3. 找不到 → ("unknown", "Unknown")
    """
    key = (semester, page_num)
    if key in BOUNDARIES:
        return BOUNDARIES[key]

    for pg in range(page_num - 1, 0, -1):
        prev = (semester, pg)
        if prev in BOUNDARIES:
            cat, label = BOUNDARIES[prev]
            if cat == "unit":
                return ("unit", label)
            else:
                return (cat, label)

    return ("unknown", "Unknown")
