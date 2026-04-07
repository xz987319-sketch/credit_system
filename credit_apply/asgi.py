"""ASGI 入口：供异步服务器（如 Daphne）加载本 Django 项目。"""  # 模块说明异步网关接口用途
import os  # 导入 os 以便读取环境变量
from django.core.asgi import get_asgi_application  # 导入 Django 提供的 ASGI 应用工厂函数

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "credit_apply.settings")  # 设置默认配置模块
application = get_asgi_application()  # 创建可供部署的 ASGI 应用实例
