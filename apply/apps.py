"""应用配置：向 Django 注册 apply 应用的元数据。"""  # 模块文档字符串
from django.apps import AppConfig  # 导入应用配置基类


class ApplyConfig(AppConfig):  # 定义应用配置类继承框架基类
    """配置应用默认自动字段与显示名称。"""  # 类文档字符串说明用途

    default_auto_field = "django.db.models.BigAutoField"  # 与全局设置保持一致避免迁移警告
    name = "apply"  # 指定应用 Python 包名供 INSTALLED_APPS 引用
    verbose_name = "信贷申请模拟"  # 在后台等处展示更友好的中文名称

    def ready(self):
        """Django 启动时导入信号处理器"""
        import apply.signals  # noqa: F401
