"""H5 进件子路由：公开申请与成功页。"""  # 模块文档字符串
from django.urls import path  # 导入 path

from apply.views import apply_h5  # 导入 H5 视图
from apply.views.multi_step_form import h5_multi_step_form_view, pinyin_convert_api, send_sms_code_api, verify_sms_code_api  # 导入H5分步表单视图和拼音API

urlpatterns = [  # H5 路由列表
    # 银行大厅（多银行列表页）
    path("", apply_h5.bank_hall, name="bank_hall"),  # /apply/ 银行大厅
    
    # 银行下的卡种列表
    path("bank/<int:bank_id>/", apply_h5.bank_card_list, name="bank_card_list"),  # /apply/bank/1/
    
    # 兼容旧路由：重定向到银行大厅
    path("products/", apply_h5.card_product_list, name="card_product_list_alt"),  # /apply/products/
    
    # 卡种详情
    path("products/<int:pk>/", apply_h5.card_product_detail, name="card_product_detail"),  # /apply/products/1/
    
    # H5申请表单
    path("apply/<int:product_id>/", h5_multi_step_form_view, name="h5_apply_with_product"),  # /apply/apply/1/
    
    # 兼容旧路由
    path("form/", h5_multi_step_form_view, name="h5_apply"),  # /apply/form/
    
    # 成功页
    path("success/<int:pk>/", apply_h5.apply_success_view, name="apply_success"),  # 成功展示页
    
    # 拼音转换API
    path("api/pinyin/", pinyin_convert_api, name="pinyin_convert"),  # /apply/api/pinyin/?name=张三

    # 短信验证码API
    path("api/sms/send/", send_sms_code_api, name="send_sms_code"),  # GET /apply/api/sms/send/?phone=13800138000
    path("api/sms/verify/", verify_sms_code_api, name="verify_sms_code"),  # POST /apply/api/sms/verify/
]
