"""进件防重：同一身份证号对同一卡种在有效持有流程内不可重复申请。"""  # 模块文档字符串
from apply.models import Application  # 导入申请模型以读取状态常量

# 视为「已持有或已进入有效审批/发卡通道」的状态：含在途与已发卡等（拒绝类状态不在此集合）
_EFFECTIVE_HOLD_STATUSES = frozenset(
    {
        Application.ST_PENDING_FIRST,  # 待初审：已有在途申请
        Application.ST_FIRST_PASS,  # 初审通过中间态
        Application.ST_PENDING_SECOND,  # 待复审：已通过初审
        Application.ST_SECOND_PASS,  # 复审通过中间态
        Application.ST_CREDIT_ING,  # 信审中
        Application.ST_ISSUED,  # 已发卡
        Application.ST_RETURNED,  # 退回补充：同一条申请仍在处理，不应再建新单
    }
)


def id_card_holds_card_product(id_card: str, card_product_id: int, exclude_pk: int | None = None) -> bool:
    """若存在另一条申请记录为同一证件号+卡种且处于有效持有相关状态则返回 True。"""
    qs = Application.objects.filter(  # 构造查询
        id_card=id_card,  # 规范化后的身份证号
        card_product_id=card_product_id,  # 卡产品主键
        status__in=_EFFECTIVE_HOLD_STATUSES,  # 仅统计阻塞重复的状态
    )
    if exclude_pk is not None:  # 编辑场景排除当前申请主键
        qs = qs.exclude(pk=exclude_pk)  # 排除自身
    return qs.exists()  # 存在即视为不可重复进件
