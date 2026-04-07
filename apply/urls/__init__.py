"""应用 URL 聚合：挂载各子模块路由到统一前缀。"""  # 模块文档字符串
from django.urls import include, path  # 导入包含与路径函数

urlpatterns = [  # 主应用 URL 列表
    path("apply/", include("apply.urls.h5_urls")),  # 公开 H5 进件挂载到 /apply/
    path("", include("apply.urls.auth_urls")),  # 认证与首页挂载到站点根
    path("", include("apply.urls.employee_urls")),  # 员工相关路径
    path("", include("apply.urls.auditor_urls")),  # 审核员路径
    path("", include("apply.urls.admin_urls")),  # 超级管理员信审路径
]
