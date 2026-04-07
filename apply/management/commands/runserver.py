"""自定义 runserver：开发环境默认使用 8080 端口。"""  # 模块文档字符串说明覆盖目的
from django.contrib.staticfiles.management.commands.runserver import (  # 从静态文件应用导入原版命令类
    Command as StaticfilesRunserverCommand,  # 别名以便继承并保留开发期静态资源服务逻辑
)


class Command(StaticfilesRunserverCommand):  # 定义子类覆盖默认端口配置
    """继承 staticfiles 的 runserver，仅将默认端口从 8000 改为 8080。"""  # 类文档字符串

    default_port = "8080"  # 设置未显式指定端口时监听的默认端口号
