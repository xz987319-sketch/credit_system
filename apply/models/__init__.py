"""模型包导出：集中暴露对外使用的 ORM 类。"""  # 包文档字符串
from apply.models.application import Application  # 导入申请模型供迁移与外键引用
from apply.models.audit_log import AuditLog  # 导入审计日志模型
from apply.models.bank import Bank  # 导入银行模型
from apply.models.card_product import CardProduct  # 导入卡产品模型
from apply.models.form_config import FormField, FormPage  # 导入表单配置模型
from apply.models.user import MenuItem, User  # 导入自定义用户模型与菜单项模型

__all__ = ["Application", "AuditLog", "Bank", "CardProduct", "FormField", "FormPage", "MenuItem", "User"]  # 定义公开 API 列表
