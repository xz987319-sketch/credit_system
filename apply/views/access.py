"""访问控制辅助：判断用户是否可查看指定银行的申请单。"""  # 模块文档字符串
from apply.models import Application  # 导入申请模型用于类型引用


def can_access_application(user, application: Application) -> bool:  # 定义权限判断函数
    """超级管理员可访问任意申请，其余用户需银行一致。"""  # 函数文档字符串
    if getattr(user, "is_superuser", False):  # 超级用户直接放行
        return True  # 返回允许访问
    bank_id = getattr(user, "bank_id", None)  # 读取用户所属银行主键
    if not bank_id:  # 未绑定银行则无权查看业务数据
        return False  # 拒绝访问
    return bank_id == application.bank_id  # 比较申请所属银行是否一致


def is_quality_inspector(user) -> bool:  # 定义审核员角色判断
    """判断用户是否为银行审核员角色。"""  # 函数文档字符串
    from apply.models import User  # 局部导入避免循环

    return getattr(user, "role", "") == User.ROLE_QUALITY  # 比较角色字段常量


def can_access_auditor_functions(user) -> bool:  # 定义可进入初审复审流程的权限
    """超级管理员或银行审核员可操作待初审、待复审相关页面。"""  # 函数文档字符串
    if getattr(user, "is_superuser", False):  # 超级用户拥有全部业务入口
        return True  # 允许访问
    return is_quality_inspector(user)  # 否则需为审核员角色
