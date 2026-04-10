"""Django 项目全局配置：数据库、应用、认证、静态资源与 Unfold 后台。"""  # 配置模块文档字符串
from pathlib import Path  # 导入路径工具用于跨平台拼接项目目录
from django.contrib.messages import constants as message_constants  # 导入消息级别常量用于 MESSAGE_TAGS 映射

BASE_DIR = Path(__file__).resolve().parent.parent  # 计算项目根目录绝对路径供模板与静态文件使用

SECRET_KEY = "demo-secret-key-change-in-production"  # 开发演示用的密钥生产环境务必更换
DEBUG = True  # 开发模式开启以便显示详细错误页面
ALLOWED_HOSTS: list[str] = ["*"]  # 演示环境允许任意主机头便于局域网访问

# 禁用 W004 警告：自定义用户按「银行+用户名」联合唯一，非全局唯一（设计如此）
SILENCED_SYSTEM_CHECKS = ["auth.W004"]

# CSRF 安全配置：信任本地开发域名
CSRF_TRUSTED_ORIGINS: list[str] = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost",
    "http://127.0.0.1",
]

# 文件上传大小限制（前端已压缩，后端作为兜底防护）
# 默认 2.5MB 太小，拍照图片会触发 RequestDataTooBig
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10MB

INSTALLED_APPS = [  # 注册已安装应用列表
    "adminsortable2",  # 注册排序支持（拖拽排序）
    "unfold",  # 注册 Unfold 以替换默认 Admin 主题
    "unfold.contrib.filters",  # 注册 Unfold 附带的过滤器组件
    "django.contrib.admin",  # 启用 Django 自带后台管理站点
    "django.contrib.auth",  # 启用认证框架与用户模型支撑
    "django.contrib.contenttypes",  # 启用内容类型系统支撑通用关联
    "django.contrib.sessions",  # 启用会话中间件存储验证码等数据
    "django.contrib.messages",  # 启用消息框架用于一次性提示
    "django.contrib.staticfiles",  # 启用静态文件收集与开发期服务
    "apply",  # 注册信贷业务主应用
]

MIDDLEWARE = [  # 定义请求响应处理中间件链顺序
    "django.middleware.security.SecurityMiddleware",  # 添加安全相关响应头
    "django.contrib.sessions.middleware.SessionMiddleware",  # 绑定会话到请求对象
    "django.middleware.locale.LocaleMiddleware",  # 激活 i18n 翻译，使 Admin 英文提示翻译为中文（须在 SessionMiddleware 后、CommonMiddleware 前）
    "django.middleware.common.CommonMiddleware",  # 处理 APPEND_SLASH 等通用逻辑
    "django.middleware.csrf.CsrfViewMiddleware",  # 校验表单 CSRF 令牌防跨站请求伪造
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # 将当前用户附加到请求
    "django.contrib.messages.middleware.MessageMiddleware",  # 将消息写入请求供模板展示
    "django.middleware.clickjacking.XFrameOptionsMiddleware",  # 降低点击劫持风险
]

ROOT_URLCONF = "credit_apply.urls"  # 指定根 URL 配置模块路径

TEMPLATES = [  # 配置模板引擎与全局上下文处理器
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",  # 使用 Django 模板后端
        "DIRS": [BASE_DIR / "apply" / "templates"],  # 追加应用模板目录便于集中管理
        "APP_DIRS": True,  # 允许从各应用内 templates 子目录自动发现模板
        "OPTIONS": {
            "context_processors": [  # 定义自动注入模板的上下文处理器列表
                "django.template.context_processors.debug",  # 注入调试相关变量
                "django.template.context_processors.request",  # 注入 request 对象
                "django.contrib.auth.context_processors.auth",  # 注入 user 与权限信息
                "django.contrib.messages.context_processors.messages",  # 注入消息列表
            ],
        },
    },
]

WSGI_APPLICATION = "credit_apply.wsgi.application"  # 指定 WSGI 应用入口路径

DATABASES = {  # 配置数据库连接参数
    "default": {  # 定义默认数据库别名
        "ENGINE": "django.db.backends.sqlite3",  # 使用 SQLite 便于毕业设计开箱即用
        "NAME": BASE_DIR / "db.sqlite3",  # 指定 SQLite 数据库文件存放位置
    }
}

AUTH_PASSWORD_VALIDATORS = [  # 配置密码强度校验器列表
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},  # 防止密码与用户信息过于相似
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},  # 限制密码最小长度
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},  # 拒绝常见弱密码
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},  # 拒绝纯数字密码
]

LANGUAGE_CODE = "zh-hans"  # 设置默认语言为简体中文，Django Admin 界面全面中文化
TIME_ZONE = "Asia/Shanghai"  # 设置默认时区为上海
USE_I18N = True  # 启用国际化翻译基础设施
USE_L10N = True  # 启用本地化格式（日期/数字按中文习惯显示）
USE_TZ = True  # 启用时区感知时间存储

STATIC_URL = "static/"  # 浏览器访问静态文件时使用的 URL 前缀
STATICFILES_DIRS = [BASE_DIR / "static"]  # 开发期额外静态文件搜索目录

# 日志文件存储目录
LOG_DIR = BASE_DIR / "logs"  # 日志文件存储目录（apply/utils/logger.py 使用）

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"  # 指定隐式主键默认使用大整型自增字段

MESSAGE_TAGS = {message_constants.ERROR: "danger"}  # 将 Django error 消息映射为 Bootstrap 的 danger 样式类

AUTH_USER_MODEL = "apply.User"  # 指定自定义用户模型以支持银行与角色字段

AUTHENTICATION_BACKENDS = [  # 定义认证后端链依次尝试登录
    "apply.auth_backends.BankBackend",  # 自定义银行号加用户名密码认证
    "django.contrib.auth.backends.ModelBackend",  # 保留默认后端供 Admin 等场景使用
]

LOGIN_URL = "apply:login"  # 未登录用户重定向到的命名 URL
LOGIN_REDIRECT_URL = "apply:home"  # 登录成功后的默认跳转地址
LOGOUT_REDIRECT_URL = "apply:login"  # 登出后的默认跳转地址

# ── 菜单可见性权限回调工厂 ────────────────────────────────────────────────────
# Unfold 的 navigation 每个 item 支持 "permission" 回调：接受 request，返回 True/False。
# 规则：
#   - 超级管理员始终可见（返回 True）
#   - 若用户的 visible_menus 为空列表，则显示全部（返回 True）
#   - 否则只有 menu_key 在 visible_menus 中才可见
def _make_menu_permission(menu_key: str):
    """生成指定菜单 key 的权限回调函数。"""
    def permission(request) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True  # 超级管理员始终可见
        # 优先从 M2M（filter_horizontal 新增）读取，否则回退到 JSONField（兼容旧数据）
        visible_items = list(
            user.visible_menu_items.values_list("key", flat=True)
        ) if hasattr(user, "visible_menu_items") else []
        if visible_items:
            return menu_key in visible_items
        # M2M 为空时回退 JSONField（已有数据迁移但保留兼容）
        visible_json = getattr(user, "visible_menus", None) or []
        if not visible_json:
            return True  # 两侧都空 = 不限制
        return menu_key in visible_json
    permission.__name__ = f"menu_perm_{menu_key}"
    return permission


UNFOLD = {  # Unfold 后台站点元信息与侧边栏分组配置
    "SITE_TITLE": "信贷流程模拟后台",  # 浏览器标签与站点标题展示文本
    "SITE_HEADER": "信贷流程模拟后台",  # 后台页眉展示文本
    "SITE_SYMBOL": "行",  # 简短符号用于折叠态展示
    "SHOW_HISTORY": True,  # 显示对象历史记录按钮
    "SHOW_VIEW_ON_SITE": False,  # 毕业设计演示关闭前台站点跳转按钮
    "STYLES": [
        lambda request: "/static/admin_custom.css",  # 注入自定义 Admin CSS
    ],
    "SIDEBAR": {  # 侧边栏结构与分组
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "导航",
                "separator": False,
                "items": [
                    {
                        "title": "首页",
                        "icon": "home",
                        "link": "/admin/",
                        "permission": _make_menu_permission("nav_home"),
                    },
                ],
            },
            {
                "title": "基础数据",
                "separator": True,
                "items": [
                    {
                        "title": "银行",
                        "icon": "account_balance",
                        "link": "/admin/apply/bank/",
                        "permission": _make_menu_permission("base_bank"),
                    },
                    {
                        "title": "用户",
                        "icon": "person",
                        "link": "/admin/apply/user/",
                        "permission": _make_menu_permission("base_user"),
                    },
                    {
                        "title": "卡产品",
                        "icon": "credit_card",
                        "link": "/admin/apply/cardproduct/",
                        "permission": _make_menu_permission("base_card"),
                    },
                ],
            },
            {
                "title": "业务流程",
                "separator": True,
                "items": [
                    {
                        "title": "信贷申请",
                        "icon": "description",
                        "link": "/admin/apply/application/",
                        "permission": _make_menu_permission("biz_apply"),
                    },
                    {
                        "title": "审核记录",
                        "icon": "history",
                        "link": "/admin/apply/auditlog/",
                        "permission": _make_menu_permission("biz_audit"),
                    },
                ],
            },
            {
                "title": "表单配置",
                "separator": True,
                "items": [
                    {
                        "title": "总表单页",
                        "icon": "table_chart",
                        "link": "/admin/apply/formpage/",
                        "permission": _make_menu_permission("form_page"),
                    },
                    {
                        "title": "子表单字段",
                        "icon": "list_alt",
                        "link": "/admin/apply/formfield/",
                        "permission": _make_menu_permission("form_field"),
                    },
                ],
            },
        ],
    },
}
