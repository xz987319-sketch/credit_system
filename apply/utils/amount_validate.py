"""申请金额后端校验：解析文本、小数位、正数及与卡种区间比对。"""  # 模块文档字符串
import re  # 导入正则用于格式检查
from decimal import Decimal, InvalidOperation  # 导入高精度小数与转换异常

from django.core.exceptions import ValidationError  # 导入校验异常

from apply.models import CardProduct  # 导入卡产品类型注解


def _format_money_pair(min_d: Decimal, max_d: Decimal) -> str:  # 内部函数格式化区间文案
    """将上下限转为「10,000.00 ～ 100,000.00」样式字符串。"""  # 文档字符串
    return f"{min_d:,.2f} ～ {max_d:,.2f}"  # 使用逗号千分位与两位小数


def validate_submitted_amount_string(raw: str, product: CardProduct | None) -> Decimal:  # 主入口
    """校验用户提交的金额字符串，返回 Decimal；失败抛出 ValidationError（含明确提示）。"""
    s = (raw or "").strip()  # 去掉首尾空白
    if not s:  # 空串视为未填写
        raise ValidationError("申请金额不能为空。")  # 空值提示
    if s.startswith("."):  # 以小数点开头时按规则补零（与前端一致）
        s = "0" + s  # 前缀补零
    if not re.fullmatch(r"\d+(\.\d{0,2})?", s):  # 仅允许整数或至多两位小数
        if "." in s and len(s.split(".", 1)[1]) > 2:  # 单独识别小数位过长
            raise ValidationError("金额最多保留两位小数。")  # 小数位提示
        raise ValidationError("请输入有效数字（仅支持数字与小数点，且不能以小数点开头）。")  # 通用格式错误
    try:  # 尝试转为 Decimal
        amount = Decimal(s)  # 解析金额
    except InvalidOperation:  # 无法解析
        raise ValidationError("请输入有效数字。")  # 兜底提示
    if amount <= 0:  # 非正数不允许
        raise ValidationError("金额不能为 0 或负数。")  # 正数约束
    if amount.as_tuple().exponent < -2:  # 理论上已被正则拦住，双保险
        raise ValidationError("金额最多保留两位小数。")  # 小数位提示
    if product is not None:  # 需要按卡种校验区间
        lo, hi = product.credit_limit_min, product.credit_limit_max  # 读取产品上下限
        if amount < lo or amount > hi:  # 越界
            raise ValidationError(  # 带具体区间提示
                f"申请金额必须在 {_format_money_pair(lo, hi)} 元之间。",  # 用户要求的句式
            )
    return amount  # 返回合法 Decimal


def resolve_card_product_from_post(post_data, field_name: str = "card_product") -> CardProduct | None:  # 辅助
    """从原始 POST 数据中解析卡种主键并返回模型实例或 None。"""
    raw_pk = post_data.get(field_name)  # 读取表单字段
    if raw_pk in (None, ""):  # 未选择
        return None  # 返回空
    try:  # 尝试转换主键
        return CardProduct.objects.get(pk=int(raw_pk))  # 查询产品
    except (TypeError, ValueError, CardProduct.DoesNotExist):  # 非法或不存在
        return None  # 视为无有效卡种
