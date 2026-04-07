"""审核员子路由：初审与复审队列及操作。"""  # 模块文档字符串
from django.urls import path  # 导入 path

from apply.views import auditor  # 导入审核视图

urlpatterns = [  # 审核员路由表
    path("pending/", auditor.pending_first_list_view, name="pending_first"),  # 待初审列表
    path("pending/<int:pk>/detail/", auditor.pending_first_detail_view, name="pending_first_detail"),  # 初审详情
    path("pending/<int:pk>/pass/", auditor.pending_first_pass_view, name="pending_first_pass"),  # 初审通过
    path("pending/<int:pk>/return/", auditor.pending_first_return_view, name="pending_first_return"),  # 初审退回
    path("second_pending/", auditor.pending_second_list_view, name="pending_second"),  # 待复审列表
    path("second_pending/<int:pk>/detail/", auditor.pending_second_detail_view, name="pending_second_detail"),  # 复审详情
    path("second_pending/<int:pk>/pass/", auditor.pending_second_pass_view, name="pending_second_pass"),  # 复审通过
    path("second_pending/<int:pk>/reject/", auditor.pending_second_reject_view, name="pending_second_reject"),  # 复审拒绝
]
