"""银行数据范围工具：为非超级用户自动限定查询所属银行。"""  # 模块文档字符串
from django.db.models import QuerySet  # 导入查询集类型注解


def scope_by_bank(queryset: QuerySet, user) -> QuerySet:  # 定义按用户银行过滤查询集函数
    """超级管理员返回原查询集，否则仅保留与用户银行匹配的记录。"""  # 函数文档字符串
    if getattr(user, "is_superuser", False):  # 判断用户是否具备超级管理员标记
        return queryset  # 超级用户不做银行过滤直接返回
    bank_id = getattr(user, "bank_id", None)  # 读取用户外键银行主键可能为空
    if not bank_id:  # 若用户未绑定银行则无法查看业务数据
        return queryset.none()  # 返回空查询集避免越权
    return queryset.filter(bank_id=bank_id)  # 按银行主键过滤后返回新查询集
