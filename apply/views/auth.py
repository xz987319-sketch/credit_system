"""认证相关视图：登录、登出与登录后首页跳转。"""  # 模块文档字符串
from django.contrib import messages  # 导入消息框架用于一次性提示
from django.contrib.auth import authenticate, login, logout  # 导入认证与登录登出函数
from django.contrib.auth.decorators import login_required  # 导入登录校验装饰器
from django.http import JsonResponse  # 导入 JSON 响应用于验证码无刷新接口
from django.shortcuts import redirect, render  # 导入重定向与渲染快捷函数
from django.views.decorators.http import require_http_methods  # 导入限制 HTTP 方法的装饰器

from apply.forms import LoginForm  # 导入登录表单类
from apply.utils.captcha import generate_captcha_text, store_captcha, captcha_matches  # 导入验证码工具


@require_http_methods(["GET", "POST"])  # 仅允许 GET 与 POST 访问登录视图
def login_view(request):  # 定义登录视图函数
    """展示登录表单并在 POST 时校验验证码与银行组合凭证。"""  # 视图文档字符串
    if request.user.is_authenticated:  # 判断用户是否已登录避免重复登录
        return redirect("apply:home")  # 已登录直接跳转首页
    if request.method == "POST":  # 判断是否为表单提交请求
        form = LoginForm(request.POST)  # 使用 POST 数据绑定表单
        if form.is_valid():  # 执行字段级校验
            bank_code = form.cleaned_data["bank_code"]  # 取出银行号
            username = form.cleaned_data["username"]  # 取出用户名
            password = form.cleaned_data["password"]  # 取出密码
            captcha_input = form.cleaned_data["captcha"]  # 取出用户输入验证码
            if not captcha_matches(request, captcha_input):  # 调用工具比对验证码
                messages.error(request, "验证码不正确")  # 提示验证码错误
            else:  # 验证码正确继续认证
                user = authenticate(  # 调用认证后端链验证用户
                    request,  # 传入请求对象
                    bank_code=bank_code,  # 传入银行号关键字参数
                    username=username,  # 传入用户名
                    password=password,  # 传入明文密码
                )
                if user is None:  # 判断认证是否失败
                    messages.error(request, "银行号、用户名或密码错误")  # 提示凭据错误
                elif not user.is_active:  # 判断账号是否被禁用
                    messages.error(request, "账号已被禁用")  # 提示状态异常
                else:  # 认证成功且账号可用
                    login(request, user)  # 建立会话登录状态
                    messages.success(request, "登录成功")  # 提示成功信息
                    return redirect("apply:home")  # 重定向到业务首页
        else:  # 表单字段校验失败
            messages.error(request, "请检查输入项是否完整")  # 提示表单错误
    else:  # GET 请求展示空白或刷新验证码
        form = LoginForm()  # 实例化空表单
    code = generate_captcha_text()  # 生成新的随机验证码字符串
    store_captcha(request, code)  # 将验证码写入会话供后续比对
    return render(request, "login.html", {"form": form, "captcha_code": code})  # 渲染模板并展示验证码


@require_http_methods(["GET"])  # 仅 GET 刷新会话验证码
def refresh_captcha_view(request):  # 定义验证码刷新接口
    """生成新验证码写入 session 并返回 JSON，供前端点击替换无需整页刷新。"""  # 视图文档字符串
    code = generate_captcha_text()  # 生成随机串
    store_captcha(request, code)  # 写入会话
    return JsonResponse({"code": code})  # 返回明文供演示页展示


@login_required  # 要求用户已登录才能访问登出
@require_http_methods(["POST"])  # 仅允许 POST 防止跨站 GET 登出
def logout_view(request):  # 定义登出视图
    """销毁当前会话并返回登录页。"""  # 视图文档字符串
    logout(request)  # 清除登录会话
    messages.info(request, "您已安全退出")  # 提示用户已登出
    return redirect("apply:login")  # 重定向到登录页


@login_required  # 首页需要登录后访问
@require_http_methods(["GET"])  # 首页仅允许 GET
def home_view(request):  # 定义业务首页视图
    """根据角色展示欢迎信息与快捷入口说明。"""  # 视图文档字符串
    return render(request, "home.html", {})  # 渲染首页模板
