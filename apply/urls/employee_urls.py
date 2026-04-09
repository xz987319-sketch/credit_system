"""员工子路由：我的申请、补充编辑与详情。"""  # 模块文档字符串
from django.urls import path  # 导入 path

from apply.views import employee  # 导入员工视图
from apply.views.multi_step_form import multi_step_form_view, pinyin_convert_api, check_duplicate_view  # 导入分步表单视图和拼音API

urlpatterns = [  # 员工端路由
    path("apply/", employee.employee_apply_view, name="employee_apply"),  # 员工信用卡申请入口
    path("loan/", employee.loan_apply_view, name="loan_apply"),  # 贷款申请入口（前台登录用户）
    path("loan/products/", employee.loan_product_list_view, name="loan_product_list"),  # PC端卡种列表
    path("loan/products/<int:pk>/", employee.loan_product_detail_view, name="loan_product_detail"),  # PC端卡种详情
    path("loan/apply/<int:product_id>/", multi_step_form_view, name="loan_apply_with_product"),  # PC端多步骤申请表单
    path("my/", employee.my_applications_view, name="my_applications"),  # 我的申请列表
    path("return/edit/<int:pk>/", employee.return_edit_view, name="return_edit"),  # 退回补充编辑（简单版）
    path("return/full/<int:pk>/", employee.return_multi_step_view, name="return_full_edit"),  # 退回完整编辑（多步骤表单）
    path("application/<int:pk>/", employee.application_detail_view, name="application_detail"),  # 申请详情比对
    # 拼音转换API
    path("api/pinyin/", pinyin_convert_api, name="pinyin_convert"),  # /employee/api/pinyin/?name=张三
    # 防重检测API
    path("api/check-duplicate/", check_duplicate_view, name="check_duplicate"),  # /employee/api/check-duplicate/?id_card=xxx&product_id=1
]
