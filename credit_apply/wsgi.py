"""WSGI 入口：供传统同步 WSGI 服务器加载本 Django 项目。"""  # 模块说明同步网关接口用途
import os  # 导入 os 以便读取环境变量
from django.core.wsgi import get_wsgi_application  # 导入 Django 提供的 WSGI 应用工厂函数

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "credit_apply.settings")  # 设置默认配置模块
application = get_wsgi_application()  # 创建可供部署的 WSGI 应用实例
