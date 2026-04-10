"""
Django Admin 注册模块
=====================
将所有业务模型注册到 Django Admin，并应用银行数据隔离权限控制。

权限架构：
  超级管理员（is_superuser=True）→ 可操作所有银行的全部数据
  普通员工                        → 只能查看/编辑自己所属银行的数据

依赖：apply.bank_scoped_mixin.BankScopedMixin（通用银行隔离逻辑）
"""

# ── Django 内置导入 ─────────────────────────────────────────────────────────
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.utils.html import mark_safe
# ^ 导入 admin 模块，提供 @admin.register 装饰器与 admin.site 注册机制。
#   admin.site 是 Django 默认的 AdminSite 单例，所有模型都注册到这里。

from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
# ^ 导入 Django 内置的 UserAdmin 基类。
#   它已经处理好了密码哈希显示、权限 Tab 等复杂逻辑，我们继承并扩展它，
#   避免重复实现用户管理的标准功能。

# ── Unfold 主题导入 ─────────────────────────────────────────────────────────
from unfold.admin import ModelAdmin
# ^ 导入 Unfold 提供的 ModelAdmin，它替换了 Django 默认样式，
#   提供更现代的 UI（玻璃效果、图标、深浅色主题等）。
#   所有 ModelAdmin 子类改为继承这个而非 django.contrib.admin.ModelAdmin。

# ── 本项目模型导入 ────────────────────────────────────────────────────────
from apply.models import Application, AuditLog, Bank, CardProduct, FormField, FormPage, MenuItem, User
# ^ 批量导入所有需要注册到 Admin 的业务模型。
#   Application  — 信贷申请主表
#   AuditLog     — 审计/审批日志
#   Bank         — 银行机构
#   CardProduct  — 信用卡产品配置
#   User         — 业务用户（含银行关联与角色）

# ── 银行隔离 Mixin 导入 ───────────────────────────────────────────────────
from apply.bank_scoped_mixin import BankScopedMixin

# ── 自定义 Widget 导入 ────────────────────────────────────────────────────
from apply.widgets import (
    ColorSelectWidget,
    MenuVisibilityField,
    MenuVisibilityWidget,
    TranslatedFilteredSelectMultiple,
    _translate_permission_name,  # 用户权限中文化翻译函数
)
# ^ 导入自定义 Widget：
#   ColorSelectWidget          — 品牌色选择器（带色块预览）
#   MenuVisibilityField/Widget  — 双栏窗口控制选择器
#   TranslatedFilteredSelectMultiple — 保留（当前方案已不依赖它，备选）
#   _translate_permission_name  — 权限名中英翻译函数（用于覆写 label_from_instance）
#   详细逻辑见 bank_scoped_mixin.py 中的逐行注释。


# ════════════════════════════════════════════════════════════════════════════
# 银行（Bank）
# ════════════════════════════════════════════════════════════════════════════

@admin.register(Bank)
# ^ @admin.register(Bank) 是装饰器语法糖，等价于：
#     admin.site.register(Bank, BankAdmin)
#   它将 Bank 模型与 BankAdmin 配置类绑定并注册到默认 Admin 站点。
class BankAdmin(BankScopedMixin, ModelAdmin):
    # ^ 继承顺序很重要！Python MRO（方法解析顺序）从左到右查找方法：
    #   BankScopedMixin 在 ModelAdmin 前面，确保 Mixin 的方法优先被找到。
    #   如果写成 (ModelAdmin, BankScopedMixin)，Mixin 的方法就会被 ModelAdmin 覆盖。
    """
    银行基础资料维护。

    特殊处理：Bank 表本身就是「根」表，没有 bank 外键字段，
    但我们需要限制普通员工只能看到自己银行的银行档案。
    因此覆盖 get_queryset 用 pk 过滤（只显示本行自身的档案行）。
    """

    list_display = ("bank_code", "bank_name", "colored_brand_color", "is_featured")
    # ^ 列表页显示的列名。
    #   bank_code: 银行编号
    #   bank_name: 银行名称
    #   colored_brand_color: 品牌色（色块+中文名）
    #   is_featured: 是否热门银行

    search_fields = ("bank_code", "bank_name")
    # ^ 支持搜索的字段。

    list_filter = ("is_featured",)
    # ^ 右侧边栏筛选器：按是否热门银行过滤。
    #   列表页列标题旁的⊗和数字是排序优先级指示器，由模型 Meta.ordering 触发，
    #   与 list_filter 无关，通过 CSS 统一隐藏（见 static/admin_custom.css）。

    change_list_template = "admin/apply/bank/change_list.html"
    # ^ 自定义模板：Filters 按钮中文

    # ── 品牌色 hex → 中文名映射 ──────────────────────────────────────
    COLOR_NAME_MAP = {
        "#e74c3c": "红色", "#c0392b": "深红色", "#e91e63": "粉红色",
        "#9c27b0": "紫色", "#9b59b6": "紫色", "#673ab7": "深紫色",
        "#3f51b5": "靛蓝色", "#3182ce": "蓝色", "#2196f3": "蓝色",
        "#03a9f4": "浅蓝色", "#00bcd4": "青色", "#009688": "青绿色",
        "#4caf50": "绿色", "#27ae60": "绿色", "#8bc34a": "浅绿色",
        "#cddc39": "黄绿色", "#ffeb3b": "黄色", "#ffc107": "琥珀色",
        "#ff9800": "橙色", "#ff5722": "深橙色", "#795548": "棕色",
        "#607d8b": "蓝灰色", "#9e9e9e": "灰色", "#000000": "黑色",
        "#ffffff": "白色",
    }

    def colored_brand_color(self, obj):
        """在列表页显示品牌色的色块与对应中文名称。"""
        hex_color = (obj.brand_color or "#3182ce").strip()
        color_name = self.COLOR_NAME_MAP.get(hex_color.lower(), hex_color)
        return mark_safe(
            f'<span style="display:inline-flex;align-items:center;gap:6px;">'
            f'<span style="display:inline-block;width:16px;height:16px;'
            f'border-radius:3px;background:{hex_color};border:1px solid #ccc;"></span>'
            f'<span>{color_name}</span>'
            f'</span>'
        )
    colored_brand_color.short_description = "品牌色"

    def get_form(self, request, obj=None, change=False, **kwargs):
        """将 brand_color 字段的 widget 替换为带色块预览的下拉选择器。"""
        from apply.models.bank import BRAND_COLOR_CHOICES
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        if "brand_color" in form.base_fields:
            field = form.base_fields["brand_color"]
            field.widget = ColorSelectWidget(choices=BRAND_COLOR_CHOICES)
            field.widget.choices = BRAND_COLOR_CHOICES
        return form

    def get_queryset(self, request):
        """
        Bank 表的特殊查询集过滤逻辑。

        与其他模型不同：Bank 表本身没有 bank 外键（它就是银行表本身），
        所以不能用通用的 filter(bank_id=...) 过滤。
        改为：普通员工只能看到自己所在银行这一行数据（filter(pk=bank_id)）。
        """
        qs = super(BankScopedMixin, self).get_queryset(request)
        # ^ 注意：这里调用的是 BankScopedMixin「再上一级」父类的 get_queryset，
        #   即 ModelAdmin.get_queryset，跳过 BankScopedMixin.get_queryset。
        #   原因：Bank 模型没有 bank 外键，通用 Mixin 的过滤逻辑（filter(bank_id=...)）
        #   对 Bank 表无效，需要在这里用专门的 pk 过滤逻辑代替。

        if request.user.is_superuser:
            # ^ 超级管理员可以看到所有银行（总行 0000 管理所有分行档案）
            return qs  # 返回全量查询集

        bank_id = getattr(request.user, "bank_id", None)
        # ^ 从当前登录用户读取所属银行的主键（整数 id）。
        #   getattr 第三个参数 None 是默认值，防止字段不存在时报 AttributeError。

        if not bank_id:
            # ^ 未绑定银行（理论上不应出现），安全起见返回空集
            return qs.none()  # 返回空查询集，确保不泄露任何数据

        return qs.filter(pk=bank_id)
        # ^ 按银行表的主键过滤，员工只能看到自己所在银行的这一条档案。
        #   这里用 pk（主键）而非 bank_id（外键），
        #   因为 Bank 表的「银行归属」就是它自己的主键。

    def has_add_permission(self, request):
        """
        银行档案的新增权限：只有超级管理员才能新增银行。

        普通员工不应该能创建新的银行机构，这是总行层面的管理操作。
        """
        if not request.user.is_superuser:
            # ^ 非超级管理员：禁止新增银行档案
            return False  # 返回 False 隐藏「新增银行」按钮
        return super().has_add_permission(request)
        # ^ 超级管理员：使用父类的默认权限判断（通常返回 True）

    def has_delete_permission(self, request, obj=None):
        """
        银行档案的删除权限：只有超级管理员才能删除银行。

        删除银行会影响关联的用户、申请等大量数据（PROTECT 外键会阻止，
        但让普通员工看到「删除」按钮本身也是安全隐患）。
        """
        if not request.user.is_superuser:
            # ^ 非超级管理员：禁止删除银行档案
            return False  # 隐藏删除按钮
        return super().has_delete_permission(request, obj)
        # ^ 超级管理员：使用父类默认权限判断


# ════════════════════════════════════════════════════════════════════════════
# 用户（User）
# ════════════════════════════════════════════════════════════════════════════

@admin.register(User)
# ^ 将 User 模型注册到 Admin
class UserAdmin(BankScopedMixin, DjangoUserAdmin, ModelAdmin):
    # ^ MRO 顺序：
    #   1. BankScopedMixin — 提供银行隔离逻辑（get_queryset, save_model 等）
    #   2. DjangoUserAdmin — 提供密码、权限等用户管理逻辑
    #   3. ModelAdmin      — Unfold 主题样式
    #
    #   为什么 BankScopedMixin 要在 DjangoUserAdmin 之前？
    #   确保银行过滤的 get_queryset 能覆盖 DjangoUserAdmin 的 get_queryset，
    #   而不是反过来被 DjangoUserAdmin 的逻辑覆盖。
    """
    用户管理 Admin。

    在 Django 标准用户管理基础上，增加银行关联字段和角色字段的展示与隔离。
    普通员工只能查看/编辑本行用户，超级管理员可管理所有用户。
    """

    list_display = ("username", "email", "bank", "role", "is_staff", "is_superuser")
    # ^ 列表页展示的列：
    #   username    — 用户名
    #   email       — 邮箱
    #   bank        — 所属银行（ForeignKey，显示 Bank.__str__ 即 "代码 名称"）
    #   role        — 角色（normal/quality_inspector，会显示 choices 中的中文）
    #   is_staff    — 是否可登录 Admin
    #   is_superuser — 是否超级管理员

    list_filter = ("role", "is_staff", "is_superuser")
    # ^ 右侧筛选器面板的字段，点击可按角色/权限类型过滤用户列表

    change_list_template = "admin/apply/user/change_list.html"
    # ^ 自定义模板：Filters 按钮中文

    search_fields = ("username", "email")
    # ^ 搜索框支持按用户名或邮箱关键字搜索

    ordering = ("username",)
    # ^ 列表默认按用户名字母顺序排序，便于快速定位

    # filter_horizontal 让 groups、user_permissions 和 visible_menu_items 以双栏选择器显示（自带左右箭头）
    # visible_menu_items（ManyToManyField）配合 filter_horizontal 实现与"组"完全一致的双栏 UI
    filter_horizontal = ("groups", "user_permissions", "visible_menu_items")

    # ── 精确重建 fieldsets（不能用 + 追加，必须显式重组以控制字段顺序）────────────
    # DjangoUserAdmin.fieldsets 中，"权限"区块包含：
    #   is_active / is_staff / is_superuser / groups / user_permissions
    # 用户要求"后台窗口控制"在「权限（有效/工作人员/超级用户）」下方、「组」上方，
    # 因此将"权限"区块拆成两段，visible_menus 插入其中。

    _PERMISSIONS_TOP = (  # 权限区第一段：状态开关 + 后台窗口控制（M2M + filter_horizontal 双栏 UI）
        "权限",
        {
            "fields": ("is_active", "is_staff", "is_superuser", "visible_menu_items"),
            "description": (
                "「后台窗口控制」右侧为空时表示不限制（显示全部菜单）；"
                "超级管理员不受此限制，始终显示全部。"
            ),
        },
    )
    _PERMISSIONS_BOTTOM = (  # 权限区第二段：组和权限（双栏选择器）
        None,
        {"fields": ("groups", "user_permissions")},
    )

    def _build_fieldsets(self, include_visible_menus: bool):
        """构建用户表单字段集，include_visible_menus=True 时才包含 visible_menu_items。"""
        base = (
            (None, {"fields": ("username", "password")}),
            ("个人信息", {"fields": ("first_name", "last_name", "email")}),
        )
        perms_top_fields = ["is_active", "is_staff", "is_superuser"]
        if include_visible_menus:
            perms_top_fields.append("visible_menu_items")
        perms_top = ("权限", {"fields": tuple(perms_top_fields)})
        perms_bottom = (None, {"fields": ("groups", "user_permissions")})
        tail = (
            ("银行与角色", {"fields": ("bank", "role")}),
            ("重要日期", {"fields": ("last_login", "date_joined")}),
        )
        return base + (perms_top, perms_bottom) + tail

    def get_fieldsets(self, request, obj=None):
        """
        编辑页字段集：visible_menus 位于「权限」状态开关下方、「组」上方。
        新增页字段集：同样包含 visible_menus。
        """
        if obj is None:
            # 新增用户
            return (
                (None, {"classes": ("wide",), "fields": ("username", "usable_password", "password1", "password2")}),
                ("个人信息", {"fields": ("first_name", "last_name", "email")}),
                ("权限", {"fields": ("is_active", "is_staff", "is_superuser", "visible_menu_items")}),
                (None, {"fields": ("groups", "user_permissions")}),
                ("银行与角色", {"fields": ("bank", "role")}),
            )
        # 编辑用户
        return self._build_fieldsets(include_visible_menus=True)

    # 不再用 formfield_overrides，改为 get_form 中动态注入 MultipleChoiceField

    # ── 用户权限字段中文化 ────────────────────────────────────────────────
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        将 user_permissions 的下拉选择器选项翻译为中文。

        Django 对 ManyToManyField 调用 formfield_for_manytomany（非 formfield_for_m2m），
        该方法内部调用 db_field.formfield() → 创建 ModelMultipleChoiceField。
        ModelChoiceIterator.choice(obj) 迭代时调用 field.label_from_instance(obj) 生成选项标签，
        默认 str(obj) → 英文权限名（如 'Can add log entry'）。

        这里直接覆写 field.label_from_instance，将英文翻译为中文。

        权限翻译示例：
          'Can add log entry'     → '可添加日志'
          'Can change bank'       → '可修改银行'
          'Can delete card product' → '可删除卡产品'
        """
        field = super().formfield_for_manytomany(db_field, request, **kwargs)

        if db_field.name == "user_permissions" and field is not None:

            def translated_label_from_instance(obj):
                return _translate_permission_name(str(obj))

            field.label_from_instance = translated_label_from_instance

        return field

    def get_queryset(self, request):
        """
        用户列表的银行隔离查询集。

        User 表有 bank_id 字段（ForeignKey → Bank），
        BankScopedMixin.get_queryset 通用逻辑完全适用，
        但这里显式覆盖是为了对 DjangoUserAdmin 的 get_queryset 取得优先权。

        MRO 说明：
          若不覆盖，Python 会先在 BankScopedMixin 找 get_queryset（能找到），
          再 super() 时调用 DjangoUserAdmin.get_queryset，
          整体上通用 Mixin 逻辑是生效的。
          显式写出来只是让代码逻辑更清晰可读。
        """
        qs = super().get_queryset(request)
        # ^ super() 按 MRO 顺序调用 BankScopedMixin.get_queryset，
        #   该方法内部再调用 DjangoUserAdmin.get_queryset，
        #   保证原有的排序等逻辑也被执行。

        return qs  # 直接返回 Mixin 已经过滤好的查询集

    def get_form(self, request, obj=None, change=False, **kwargs):
        """
        用户表单：
          - 调用 BankScopedMixin.get_form 处理 bank 字段限制（只读/自动填充）
          - visible_menu_items 为 ManyToManyField，Django 的 filter_horizontal 自动渲染为双栏选择器
        """
        return super().get_form(request, obj=obj, change=change, **kwargs)

    def save_model(self, request, obj, form, change):
        """
        保存用户时强制设置 bank 字段。

        复用 BankScopedMixin.save_model：
        对普通员工，无论表单提交了什么银行值，
        后端都会用 request.user.bank_id 覆盖，防止跨行数据污染。
        """
        super().save_model(request, obj, form, change)
        # ^ 调用 BankScopedMixin.save_model（MRO 第一个 save_model）。
        #   Mixin 的 save_model 会先强制设置 bank_id，
        #   再调用 DjangoUserAdmin.save_model 执行实际的 obj.save()。


# ════════════════════════════════════════════════════════════════════════════
# 菜单项（MenuItem）—— 后台窗口控制的选项来源
# ════════════════════════════════════════════════════════════════════════════


@admin.register(MenuItem)
class MenuItemAdmin(ModelAdmin):
    """菜单项管理：定义哪些窗口可分配给普通员工（超级管理员不受限）。"""
    list_display = ("key", "group", "name")
    list_filter = ("group",)
    search_fields = ("key", "name")
    ordering = ("group", "name")


# ════════════════════════════════════════════════════════════════════════════
# 卡产品（CardProduct）
# ════════════════════════════════════════════════════════════════════════════

@admin.register(CardProduct)
# ^ 注册卡产品模型
class CardProductAdmin(BankScopedMixin, ModelAdmin):
    # ^ CardProduct 模型有 bank 外键，直接应用通用 Mixin 即可获得全部隔离能力：
    #   - 列表只显示本行卡产品
    #   - 表单 bank 字段只读/预填
    #   - 保存时强制使用本行 bank
    #   - 跨行对象的编辑/删除/查看权限均被拦截
    """
    信用卡产品配置管理。

    每家银行配置各自的卡种（金卡、白金卡等），
    普通员工只能管理本行的卡产品配置，不能查看或修改其他银行的产品。
    """

    list_display = (
        "product_name",   # 产品名称，如"工行白金卡"
        "bank",           # 所属银行（ForeignKey，显示银行代码+名称）
        "product_type",   # 产品类型，如"白金卡""金卡"
        "credit_limit_min",  # 最低可申请额度（元）
        "credit_limit_max",  # 最高可申请额度（元）
        "is_active",      # 是否启用（布尔值，显示勾选图标）
    )
    # ^ 以上字段均来自 CardProduct 模型定义

    list_filter = ("is_active", "bank")
    # ^ 右侧筛选器：
    #   is_active — 按"是否启用"过滤（是/否两个选项）
    #   bank      — 按银行过滤（超管可见所有银行；普通员工因列表已过滤，
    #               此处只会显示本行，但显式保留以防 Mixin 过滤失效时的二次保障）

    change_list_template = "admin/apply/cardproduct/change_list.html"
    # ^ 自定义模板：Filters 按钮中文

    search_fields = ("product_name", "product_type")
    # ^ 支持按产品名称和产品类型关键字搜索


# ════════════════════════════════════════════════════════════════════════════
# 信贷申请（Application）
# ════════════════════════════════════════════════════════════════════════════

@admin.register(Application)
# ^ 注册申请模型
class ApplicationAdmin(BankScopedMixin, ModelAdmin):
    # ^ Application 模型有 bank 外键，完全适用通用 Mixin。
    #   申请单是核心业务数据，银行隔离尤其重要：
    #   绝对不能让 A 银行员工看到 B 银行的申请人信息和申请详情。
    """
    信贷申请记录管理。

    主要用于演示和审核，普通员工只能查看本行申请，
    敏感字段（创建时间、更新时间、发卡快照）设为只读防止误改。
    card_product 字段下拉框按当前用户银行过滤，防止跨行选卡。
    """

    list_display = (
        "id",             # 申请 ID（主键）
        "applicant_name", # 申请人姓名
        "id_card",        # 证件号码
        "phone",          # 手机号
        "bank",           # 所属银行
        "status",         # 当前状态（choices 会显示中文，如"待初审""已发卡"）
        "return_reason",  # 退回原因
        "amount",         # 申请额度（元）
        "created_at",     # 申请提交时间
    )

    list_filter = ("status", "bank")
    # ^ 按状态和银行过滤，帮助管理员快速找到特定状态的申请

    list_editable = ("status",)
    # ^ 超级管理员可在列表页直接修改申请状态（兜底操作）

    search_fields = ("applicant_name", "id_card", "phone")
    # ^ 支持按申请人姓名、证件号码、手机号搜索

    search_help_text = "搜索申请人姓名、证件号码或手机号"
    # ^ 搜索框提示文字

    # 自定义模板：覆盖 Filters 按钮为中文
    change_list_template = "admin/apply/application/change_list.html"

    readonly_fields = ("created_at", "updated_at", "issue_data")
    # ^ 设为只读的字段：
    #   created_at  — 创建时间由数据库 auto_now_add 设置，不应手动修改
    #   updated_at  — 更新时间由 auto_now 自动维护，不应手动修改
    #   issue_data  — 发卡 JSON 快照，由程序自动写入，手动编辑可能破坏格式

    def get_form(self, request, obj=None, change=False, **kwargs):
        """
        覆盖表单，限制 card_product 下拉框只显示当前用户银行的卡产品。

        BankScopedMixin 已处理 bank 字段的只读/过滤。
        此处额外处理 card_product 的 queryset，确保：
          - 普通员工只能选择自己银行发行的卡产品
          - 超级管理员可选所有银行的卡产品
        """
        # 先调用 Mixin 的 get_form，完成 bank 字段的只读处理
        form = super().get_form(request, obj=obj, change=change, **kwargs)

        # 获取当前用户所属银行，用于过滤 card_product queryset
        user_bank = getattr(request.user, "bank", None)

        # card_product 字段仅在用户已绑定银行时才需要过滤下拉选项
        if user_bank is not None and "card_product" in form.base_fields:
            form.base_fields["card_product"].queryset = CardProduct.objects.filter(
                bank=user_bank,   # 仅当前用户银行的卡产品
                is_active=True,   # 仅启用中的产品
            )

        return form


# ════════════════════════════════════════════════════════════════════════════
# 审计日志（AuditLog）
# ════════════════════════════════════════════════════════════════════════════

@admin.register(AuditLog)
# ^ 注册审计日志模型
class AuditLogAdmin(BankScopedMixin, ModelAdmin):
    # ^ AuditLog 没有直接的 bank 外键，而是通过 application（外键）→ bank 关联。
    #   通用 Mixin 的 get_queryset 会检测到 AuditLog 没有 bank_id 字段，
    #   因此我们需要在下面显式覆盖 get_queryset，用跨表过滤（application__bank_id）。
    #
    #   其他 Mixin 方法（save_model、has_*_permission）对无 bank 字段的模型
    #   会自动跳过（Mixin 内部有 _model_has_bank_field 检查），不会报错。
    """
    审计日志查看。

    日志通过其关联的申请单间接属于某一家银行。
    普通员工只能查看本行申请相关的审核日志。
    日志通常不允许删除（audit trail 完整性），只读展示。
    """

    list_display = (
        "id",              # 日志 ID
        "application",     # 关联的申请单
        "audit_type",      # 审核类型（初审/复审/信审）
        "result",          # 审核结果（通过/拒绝/退回）
        "previous_status_display",  # 操作前状态（中文）
        "new_status_display",      # 操作后状态（中文）
        "comment",         # 备注说明
        "auditor",         # 审批人
        "created_at",      # 记录创建时间
    )

    list_filter = (
        ("audit_type"),     # 按审核类型筛选
        ("result"),         # 按审核结果筛选
        ("created_at"),     # 按时间筛选
    )
    # ^ 列表页筛选器：审核类型、审核结果、记录时间

    search_fields = (
        "result",             # 审核结果
        "comment",            # 审核意见
        "application__applicant_name",  # 申请人姓名
        "auditor__username",  # 审批人
    )

    # 搜索说明文字
    search_help_text = "搜索申请人、审批人、审核结果或意见"

    # 自定义模板：覆盖 Filters 按钮为中文
    change_list_template = "admin/apply/auditlog/change_list.html"

    readonly_fields = ("application", "auditor", "audit_type", "result", "previous_status", "new_status", "comment", "created_at")
    # ^ 所有字段设为只读：
    #   审计日志是操作历史记录，应当不可篡改，后台只用于查阅。
    #   设为 readonly_fields 后，表单中所有字段显示为文本（不可编辑）。

    def previous_status_display(self, obj):
        """显示操作前状态的中文名称"""
        status_map = dict(Application.STATUS_CHOICES)
        return status_map.get(obj.previous_status, obj.previous_status or "—")
    previous_status_display.short_description = "操作前状态"

    def new_status_display(self, obj):
        """显示操作后状态的中文名称"""
        status_map = dict(Application.STATUS_CHOICES)
        return status_map.get(obj.new_status, obj.new_status or "—")
    new_status_display.short_description = "操作后状态"

    def get_queryset(self, request):
        """
        AuditLog 的特殊查询集过滤逻辑。

        因为 AuditLog 没有直接的 bank 外键，
        需要通过关联的 application 跨表过滤：
          filter(application__bank_id=<当前用户银行 id>)
        即「只显示银行 ID 为 X 的申请所产生的审计日志」。

        这里我们跳过 BankScopedMixin.get_queryset（因为它不适用于无直接 bank 字段的模型），
        直接调用 ModelAdmin.get_queryset 获取基础查询集。
        """
        qs = super(BankScopedMixin, self).get_queryset(request)
        # ^ super(BankScopedMixin, self) 跳过 BankScopedMixin，
        #   直接调用 MRO 中下一个类（ModelAdmin）的 get_queryset。
        #   这样可以获得未经银行过滤的基础查询集，再由我们手动过滤。

        if request.user.is_superuser:
            # ^ 超级管理员查看所有银行的审计日志，不过滤
            return qs  # 返回全量日志

        bank_id = getattr(request.user, "bank_id", None)
        # ^ 获取当前用户所属银行的主键

        if not bank_id:
            # ^ 未绑定银行，安全起见返回空集
            return qs.none()  # 返回空日志列表

        return qs.filter(application__bank_id=bank_id)
        # ^ 跨表过滤：
        #   application__bank_id 等价于 SQL：
        #     INNER JOIN application ON auditlog.application_id = application.id
        #     WHERE application.bank_id = <bank_id>
        #   Django ORM 的双下划线 __ 语法可以穿透外键关系进行跨表查询。
        #   这样只有「属于当前用户所在银行的申请」所生成的日志才会显示。

    def has_add_permission(self, request):
        """
        审计日志不允许手动新增。

        日志应由业务流程自动产生，后台手动添加会破坏 audit trail 完整性。
        """
        return False
        # ^ 直接返回 False，隐藏「新增审计日志」按钮。
        #   无论超级管理员还是普通员工都不能手动创建日志。

    def has_delete_permission(self, request, obj=None):
        """
        审计日志不允许删除。

        合规要求：审计记录必须保留，不能被删除。
        即使是超级管理员也不应从 Admin 界面删除日志。
        """
        return False
        # ^ 直接返回 False，隐藏所有删除操作（列表页的批量删除也会被隐藏）。

    def has_change_permission(self, request, obj=None):
        """
        审计日志不允许编辑。

        配合 readonly_fields 的 UI 限制，这里从权限层面彻底禁止编辑操作。
        即使用户知道编辑页的 URL，也无法提交修改。
        """
        return False
        # ^ 直接返回 False，隐藏并禁止编辑按钮。
        #   用户仍然可以点开详情（has_view_permission 默认允许），但无法修改。


# ════════════════════════════════════════════════════════════════════════════
# 表单配置（FormPage + FormField）
# ════════════════════════════════════════════════════════════════════════════

from unfold.admin import TabularInline  # 导入 Unfold 风格的内联


class FormFieldInline(TabularInline):
    """子表单字段内联 — 在总表单页详情页内直接编辑字段列表。"""
    model = FormField
    extra = 1  # 默认显示 1 个空行供快速新增
    ordering = ("sort_order",)

    # 不包含 min_photos/max_photos 的字段列表
    BASE_FIELDS = ("field_label", "field_key", "field_type", "validation_rule", "is_required", "sort_order", "max_length", "is_active")
    # 包含 min_photos/max_photos 的字段列表（仅影像采集页使用）
    IMAGE_FIELDS = ("field_label", "field_key", "field_type", "validation_rule", "is_required", "sort_order", "max_length", "min_photos", "max_photos", "is_active")

    def get_fields(self, request, obj=None):
        """根据页面标题判断是否显示图片张数字段。"""
        if obj and "影像采集" in (obj.page_title or ""):
            return self.IMAGE_FIELDS
        return self.BASE_FIELDS

    class Media:
        css = {
            'all': ('admin_field_width.css',)
        }


@admin.register(FormPage)
class FormPageAdmin(ModelAdmin):
    """总表单页管理 — 维护进件申请表单的页面结构，支持拖拽排序。"""

    list_display = ("drag_handle", "title_link", "page_desc")
    list_display_links = None  # 禁用默认链接，使用自定义链接
    list_editable = ()  # 不使用 inline 编辑
    ordering = ("order",)
    inlines = [FormFieldInline]

    class Media:
        js = ("/static/admin_drag_sort.js",)

    # 拖拽把手列
    def drag_handle(self, obj):
        return mark_safe(
            f'<span class="drag-handle" data-id="{obj.pk}" data-order="{obj.order}" title="拖拽排序">'
            f'  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">'
            f'    <circle cx="2" cy="2" r="1"/><circle cx="6" cy="2" r="1"/><circle cx="10" cy="2" r="1"/>'
            f'    <circle cx="2" cy="6" r="1"/><circle cx="6" cy="6" r="1"/><circle cx="10" cy="6" r="1"/>'
            f'    <circle cx="2" cy="10" r="1"/><circle cx="6" cy="10" r="1"/><circle cx="10" cy="10" r="1"/>'
            f'  </svg>'
            f'</span>'
        )
    drag_handle.short_description = "排序"
    drag_handle.allow_tags = True

    # 页面标题 - 带链接可点击
    def title_link(self, obj):
        url = f'/admin/apply/formpage/{obj.pk}/change/'
        return mark_safe(f'<a href="{url}" class="title-link">{obj.__str__()}</a>')
    title_link.short_description = "页面标题"
    title_link.allow_tags = True

    # 页面说明
    def page_desc(self, obj):
        return obj.description or ""
    page_desc.short_description = "页面说明"

    # 添加拖拽排序的 API 端点
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('drag-sort/', self.admin_site.admin_view(self.drag_sort_view), name='formpage_drag_sort'),
        ]
        return custom_urls + urls

    def drag_sort_view(self, request):
        """处理拖拽排序请求"""
        import json
        from django.http import JsonResponse
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                orders = data.get('orders', [])
                for item in orders:
                    FormPage.objects.filter(pk=item['id']).update(order=item['order'])
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        return JsonResponse({'success': False, 'error': 'Method not allowed'})


@admin.register(FormField)
class FormFieldAdmin(ModelAdmin):
    """子表单字段管理 — 维护每个表单页的具体字段定义。"""

    list_display = ("page", "field_label", "field_key", "field_type", "validation_rule", "is_required", "is_readonly", "sort_order", "max_length", "is_active")
    list_display_links = ("page", "field_label")
    list_filter = ("page", "field_type", "validation_rule", "is_required", "is_readonly", "is_active")
    change_list_template = "admin/apply/formfield/change_list.html"
    # ^ 自定义模板：Filters 按钮中文
    search_fields = ("field_label", "field_key")
    ordering = ("page__order", "sort_order")
    list_editable = ("field_key", "field_type", "validation_rule", "is_required", "is_readonly", "sort_order", "max_length")

    class Media:
        css = {
            'all': ('admin_field_width.css',)
        }
