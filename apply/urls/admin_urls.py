"""超级管理员业务子路由：信审队列与操作。"""  # 模块文档字符串
from django.urls import path  # 导入 path

from apply.views import admin_views  # 导入管理员业务视图

urlpatterns = [  # 信审路由列表
    path("credit_pending/", admin_views.credit_pending_list_view, name="credit_pending"),  # 待信审列表
    path("credit_pending/<int:pk>/detail/", admin_views.credit_pending_detail_view, name="credit_pending_detail"),  # 信审详情
    path("credit_pending/<int:pk>/pass/", admin_views.credit_pass_view, name="credit_pass"),  # 信审通过
    path("credit_pending/<int:pk>/reject/", admin_views.credit_reject_view, name="credit_reject"),  # 信审拒绝
]
