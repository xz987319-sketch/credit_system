"""认证子路由：登录、登出与首页。"""  # 模块文档字符串
from django.urls import path  # 导入路径函数

from apply.views import auth  # 导入认证视图模块

urlpatterns = [  # 定义认证相关 URL 列表
    path("login/", auth.login_view, name="login"),  # 登录页路径
    path("login/captcha/refresh/", auth.refresh_captcha_view, name="refresh_captcha"),  # 点击刷新验证码 JSON
    path("logout/", auth.logout_view, name="logout"),  # 登出处理路径
    path("", auth.home_view, name="home"),  # 业务首页根路径
]
