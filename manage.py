#!/usr/bin/env python  # 指定使用环境变量中的 Python 解释器以提升跨平台可移植性
"""Django 命令行入口：用于启动开发服务器与执行迁移等管理任务。"""  # 模块文档字符串说明本文件职责
import os  # 导入操作系统接口模块以便读取环境变量
import sys  # 导入解释器相关模块以便调整模块搜索路径


def main() -> None:  # 定义主函数封装启动逻辑且不返回值
    """将 DJANGO_SETTINGS_MODULE 指向项目配置并执行命令行工具。"""  # 说明函数用途
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "credit_apply.settings")  # 若未设置则指定默认配置模块路径
    try:  # 尝试导入并执行 Django 管理命令
        from django.core.management import execute_from_command_line  # 导入命令行执行函数
    except ImportError as exc:  # 捕获导入失败异常并给出友好提示
        raise ImportError(  # 抛出更明确的导入错误帮助用户排查环境
            "无法导入 Django，请确认已安装并激活虚拟环境。"  # 中文错误信息说明常见原因
        ) from exc  # 保留原始异常链便于调试
    execute_from_command_line(sys.argv)  # 将命令行参数交给 Django 执行对应子命令


if __name__ == "__main__":  # 判断当前模块是否作为主程序直接运行
    main()  # 调用主函数启动管理命令流程
