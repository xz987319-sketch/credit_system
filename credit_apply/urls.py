"""项目根 URL 配置：挂载主应用路由与 Django 管理站点。"""  # 模块文档字符串说明职责
from django.contrib import admin  # 导入 admin 模块以注册默认管理站点路径
from django.urls import include, path  # 导入路径包含与路径定义函数

urlpatterns = [  # 定义根级 URL 模式列表
    path("admin/", admin.site.urls),  # 将后台管理站点挂载到 /admin/ 前缀下
    path("", include(("apply.urls", "apply"), namespace="apply")),  # 引入 apply 应用路由并设置命名空间
]
