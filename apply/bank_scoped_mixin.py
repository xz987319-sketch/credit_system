"""
银行数据隔离权限 Mixin
======================
业务规则：
  - 超级管理员（is_superuser=True，通常对应银行代码 0000 的总行账号）
    可以查看、新增、修改、删除所有银行的数据。
  - 普通员工只能查看/编辑「自己所属银行」的数据，
    且 bank 字段在表单中自动填充为本行，无法手动选择其他银行。
  - 未绑定银行的非超级用户视为权限不足，返回空数据集。

使用方式：
  class MyModelAdmin(BankScopedMixin, ModelAdmin):
      ...
"""

# ── 标准库导入 ──────────────────────────────────────────────────────────────
# （本模块无标准库依赖，留此注释便于后续扩展）

# ── Django 核心导入 ─────────────────────────────────────────────────────────
from django import forms           # 导入 forms 模块，用于自定义表单字段行为
from django.contrib import messages  # 导入消息框架，用于在保存后向用户显示提示
from django.core.exceptions import PermissionDenied  # 导入权限异常，越权操作时抛出


class BankScopedMixin:
    """
    通用银行数据隔离 Mixin。

    将此 Mixin 混入任意 ModelAdmin，即可自动实现：
      1. get_queryset  — 普通员工只能看到本行数据
      2. get_form      — bank 外键字段对普通员工只读/自动填充
      3. save_model    — 保存时强制将 bank 设为当前用户所在银行（防绕过）
      4. has_change_permission / has_delete_permission — 跨行对象禁止编辑/删除

    子类（具体 ModelAdmin）无需重复实现上述逻辑，只需 mixin 即可。

    前提条件：
      - 目标模型（self.model）必须有 `bank` 外键字段（ForeignKey → Bank）。
      - 登录用户模型必须有 `bank_id` 属性（即 User.bank ForeignKey 存在）。
      - 若模型使用不同的银行关联字段名，可在子类中覆盖类属性
        `bank_field_name = "your_field_name"（默认 "bank"）。
    """

    # ── 可覆盖的类属性 ────────────────────────────────────────────────────
    bank_field_name: str = "bank"
    # ^ 目标模型中银行外键的字段名，默认为 "bank"。
    #   若某个模型使用 "issuing_bank" 之类的字段名，
    #   只需在该 ModelAdmin 子类中写 bank_field_name = "issuing_bank"。

    # ═══════════════════════════════════════════════════════════════════════
    # 内部工具方法
    # ═══════════════════════════════════════════════════════════════════════

    def _get_user_bank_id(self, request) -> int | None:
        """
        从当前请求的用户对象中安全地读取所属银行的主键（id）。

        返回值：
          - int：用户绑定的银行主键，可以直接用于 ORM filter(bank_id=...)。
          - None：用户未绑定银行（通常是超级管理员不设银行，或数据异常）。

        为何用 getattr 而不是直接 request.user.bank_id？
          因为 Django 的 AUTH_USER_MODEL 可能被替换，不同项目的用户模型字段不同。
          使用 getattr(obj, attr, default) 安全取值，若字段不存在返回 None
          而不会抛 AttributeError，提高 Mixin 的可复用性。
        """
        return getattr(request.user, f"{self.bank_field_name}_id", None)
        # ^ f"{self.bank_field_name}_id" 在默认情况下等于 "bank_id"。
        #   Django ORM 对 ForeignKey 字段 bank 自动生成同名 _id 属性存储外键值。
        #   例如：user.bank_id 直接读取整数主键，比 user.bank.id 少一次数据库查询。

    def _is_superuser(self, request) -> bool:
        """
        判断当前用户是否为超级管理员。

        使用 Django 内置的 is_superuser 标志位，该值在用户创建时设定，
        超级管理员不受银行隔离限制，可以访问所有数据。
        """
        return bool(request.user.is_superuser)
        # ^ bool() 防御性转换，确保无论 is_superuser 返回何种 truthy 值都能正常比较。

    def _model_has_bank_field(self) -> bool:
        """
        检查目标模型是否真正存在名为 self.bank_field_name 的字段。

        目的：避免将此 Mixin 误用到没有 bank 字段的模型上时，
        产生难以排查的 FieldError 或过滤错误。
        """
        return hasattr(self.model, f"{self.bank_field_name}_id")
        # ^ 与 _get_user_bank_id 相同原理：Django 为每个 ForeignKey 字段
        #   生成 <field_name>_id 属性，若该属性存在则说明模型有此外键。
        #   比调用 self.model._meta.get_field(...) 更简洁，且不需要 try/except。

    # ═══════════════════════════════════════════════════════════════════════
    # 1. 数据列表过滤 — get_queryset
    # ═══════════════════════════════════════════════════════════════════════

    def get_queryset(self, request):
        """
        覆盖 ModelAdmin.get_queryset，根据当前用户的银行权限过滤可见数据。

        调用时机：Admin 列表页（changelist）加载时，Django 调用此方法获取数据集。

        过滤逻辑：
          - 超级管理员 → 返回全量查询集（不过滤）
          - 普通员工   → 只返回 bank_id 等于本人所属银行的记录
          - 未绑定银行 → 返回空查询集（.none()），彻底隔离数据
        """
        qs = super().get_queryset(request)
        # ^ 先调用父类 get_queryset，获取 Unfold/Django 默认添加的
        #   排序、select_related 等优化后的基础查询集。
        #   不能跳过这一步，否则会丢失父类的性能优化配置。

        if self._is_superuser(request):
            # ^ 超级管理员特权通道：直接返回完整数据，不做任何过滤。
            #   超级管理员在系统中对应总行账号（银行代码 0000），
            #   可以看到/管理所有银行的数据，这是业务设计的核心规则。
            return qs  # 直接返回父类的完整查询集

        if not self._model_has_bank_field():
            # ^ 安全检查：目标模型没有 bank 字段时无法过滤，
            #   为了防止误暴露数据，返回空集合而非抛出异常。
            #   这种情况通常意味着开发者把 Mixin 用错了模型，
            #   空集合能让问题在测试阶段即被发现。
            return qs.none()  # 模型无银行字段，返回空集

        bank_id = self._get_user_bank_id(request)
        # ^ 获取当前登录用户所属银行的主键（整数 id）。
        #   例如：用户属于"工商银行"，其 bank_id = 3（数据库主键），
        #   之后用这个 3 来过滤同银行的所有记录。

        if not bank_id:
            # ^ 若 bank_id 为 None 或 0（Falsy 值），说明该用户未绑定银行。
            #   正常业务中不应出现此情况（创建用户时必须选银行），
            #   但为了安全，未绑定银行的非超管用户一律返回空集，
            #   而不是意外地看到全部数据。
            return qs.none()  # 未绑定银行，返回空集合

        filter_kwargs = {f"{self.bank_field_name}_id": bank_id}
        # ^ 动态构造过滤字典，键名为 "<bank_field_name>_id"。
        #   默认情况下等于 {"bank_id": bank_id}，即按银行主键过滤。
        #   使用字典而非直接写 filter(bank_id=bank_id)，
        #   是为了支持子类修改 bank_field_name 后仍然正确过滤。
        #   例：若子类设 bank_field_name = "issuing_bank"，
        #   则 filter_kwargs = {"issuing_bank_id": bank_id}。

        return qs.filter(**filter_kwargs)
        # ^ 返回只包含本行记录的查询集。
        #   **filter_kwargs 将字典解包为关键字参数传给 .filter()，
        #   等价于 qs.filter(bank_id=bank_id)（默认情况）。

    # ═══════════════════════════════════════════════════════════════════════
    # 2. 表单 bank 字段限制 — get_form
    # ═══════════════════════════════════════════════════════════════════════

    def get_form(self, request, obj=None, change=False, **kwargs):
        """
        覆盖 ModelAdmin.get_form，对普通员工的 bank 字段做以下处理：
          a. 将查询集限制为「仅本行」（防止下拉选择其他银行）
          b. 将字段设为只读样式（禁用交互，配合 CSS 显示灰色）
          c. 设置初始值为本人所属银行（自动填充，用户无需手动选择）

        调用时机：Django 渲染新增/编辑表单时，调用此方法生成 Form 类。

        参数说明：
          obj    — 被编辑的对象，新增时为 None，编辑时为已存在的模型实例。
          change — 是否为编辑操作（True=编辑，False=新增）。
          kwargs — 其他参数透传给父类。
        """
        Form = super().get_form(request, obj=obj, change=change, **kwargs)
        # ^ 先获取父类生成的 Form 类（包含所有字段定义）。
        #   我们要在这个基础上修改 bank 字段，而不是从头构建 Form，
        #   以保留父类对字段顺序、验证等的处理。

        if self._is_superuser(request):
            # ^ 超级管理员：不限制 bank 下拉，可以选择任意银行，直接返回原始 Form。
            return Form  # 超管不受限制，直接使用原始表单

        bank_field_name = self.bank_field_name
        # ^ 取出银行字段名（通常是 "bank"），后续多处使用，
        #   存为局部变量避免重复调用 self.bank_field_name。

        if bank_field_name not in Form.base_fields:
            # ^ 检查表单是否包含 bank 字段。
            #   某些 ModelAdmin 可能通过 exclude 或 readonly_fields 隐藏了 bank 字段，
            #   此时 base_fields 中不存在该字段，跳过处理以防 KeyError。
            return Form  # 表单无此字段，无需修改

        bank_id = self._get_user_bank_id(request)
        # ^ 获取当前用户所属银行的主键，用于限制下拉查询集和设置初始值。

        if not bank_id:
            # ^ 未绑定银行的用户不应能打开新增/编辑表单，
            #   但若前端绕过列表检查直接访问 URL，这里做兜底处理。
            return Form  # 安全兜底，无法确定银行时不修改表单

        # ── 修改 bank 字段属性 ──────────────────────────────────────────
        from apply.models import Bank  # 在函数内部导入避免循环导入
        # ^ 为什么不在文件顶部 import？
        #   Bank 模型在 apply.models 中，admin.py / mixin.py 也在 apply 包下，
        #   若在模块顶部相互导入可能产生 ImportError（循环依赖）。
        #   在函数体内延迟导入可以安全绕过此问题，
        #   因为此时 Django 已完成应用注册，所有模型均已加载。

        bank_field = Form.base_fields[bank_field_name]
        # ^ 获取表单中的 bank 字段对象（ModelChoiceField 实例）。
        #   base_fields 是类属性字典，包含所有字段定义。
        #   修改 base_fields 中的字段会影响该 Form 类的所有实例，
        #   因此下面会先 deepcopy 再修改，避免污染原始 Form 类。

        import copy  # 导入标准库 copy 模块，用于深度拷贝字段对象
        bank_field = copy.deepcopy(bank_field)
        # ^ 深度拷贝字段对象！这是关键步骤。
        #   如果直接修改 Form.base_fields[bank_field_name]，
        #   会修改整个 Form 类的类属性，影响所有后续请求（包括超管的请求）。
        #   深度拷贝后，我们修改的是本次请求专属的副本，不影响其他请求。

        bank_field.queryset = Bank.objects.filter(pk=bank_id)
        # ^ 将 bank 字段的查询集限制为「只含本人所属银行」的 QuerySet。
        #   下拉列表中只会出现这一个选项，用户无法选择其他银行。
        #   Bank.objects.filter(pk=bank_id) 返回包含本行的 QuerySet（非单个对象），
        #   ModelChoiceField.queryset 要求传入 QuerySet 而非单个实例。

        bank_field.initial = bank_id
        # ^ 设置字段初始值为本人银行主键，使下拉框默认选中本行。
        #   对新增表单（obj=None）：用户打开页面时 bank 已经预选好。
        #   对编辑表单（obj=已有对象）：显示当前记录的银行（只有本行一个选项）。

        bank_field.widget.attrs["disabled"] = True
        # ^ 给 HTML <select> 添加 disabled 属性，使下拉框变灰且不可点击。
        #   这是前端 UI 层面的限制，配合 save_model 的后端校验形成双重防护。
        #   注意：disabled 字段在 HTML 提交时不会发送值，
        #   所以 save_model 中需要补充设置 bank 字段（详见 save_model 注释）。

        bank_field.required = False
        # ^ 将字段设为非必填。
        #   原因：disabled 的 <select> 不会在 POST 数据中提交值，
        #   如果 required=True，Django 表单验证会报错（"此字段是必填项"）。
        #   设为 False 后，表单验证跳过空值检查，
        #   真正的值由 save_model 在后端强制设置（安全）。

        Form.base_fields[bank_field_name] = bank_field
        # ^ 将修改后的字段副本写回 Form 类，替换原始字段。
        #   因为我们在上面做了 deepcopy，这里替换的是本次请求专属的副本，
        #   不会影响其他请求的 Form 类。

        return Form  # 返回已修改的 Form 类供 Django 渲染表单

    # ═══════════════════════════════════════════════════════════════════════
    # 3. 保存时强制覆盖 — save_model（核心安全层）
    # ═══════════════════════════════════════════════════════════════════════

    def save_model(self, request, obj, form, change):
        """
        覆盖 ModelAdmin.save_model，在写入数据库前强制将 bank 设为当前用户所在银行。

        这是整个权限控制的「最后一道防线」：
          - 即使前端构造了伪造的 bank 字段值（跳过表单 disabled 限制）
          - 即使用户直接发送 HTTP POST 请求尝试篡改 bank
          - 后端在保存时仍会用当前登录用户的 bank 覆盖提交的值

        调用时机：管理员点击「保存」按钮，表单验证通过后，写数据库之前调用此方法。

        参数说明：
          obj    — 待保存的模型实例（字段已被表单数据填充）。
          form   — 已验证的表单实例。
          change — True=编辑已有记录，False=新增记录。
        """
        if not self._is_superuser(request):
            # ^ 仅对非超级管理员做银行强制赋值。
            #   超级管理员在新增/编辑时可以自由选择 bank，不受此限制。
            #   这个 if 分支的代码只在普通员工保存时执行。

            if self._model_has_bank_field():
                # ^ 再次检查模型是否有 bank 字段，防御性编程。
                #   如果模型没有 bank 字段却赋值，会抛出 AttributeError，
                #   所以先检查再操作。

                bank_id = self._get_user_bank_id(request)
                # ^ 获取当前登录用户所属银行的主键（整数）。

                if bank_id:
                    # ^ 只有在成功获取到银行 id 时才赋值。
                    #   若 bank_id 为 None（未绑定银行），不做处理，
                    #   让 Django 的模型层校验捕获空值错误。

                    setattr(obj, f"{self.bank_field_name}_id", bank_id)
                    # ^ 使用 setattr 动态设置模型实例的 bank_id 属性。
                    #   等价于 obj.bank_id = bank_id（默认情况）。
                    #   为何用 setattr 而不直接写 obj.bank_id？
                    #   因为 bank_field_name 可被子类修改（如 "issuing_bank"），
                    #   使用 setattr 可以根据 bank_field_name 动态设置正确的字段。
                    #
                    #   注意：设置 _id 属性（外键列）而非外键对象本身（obj.bank = Bank(...)）。
                    #   直接设置 _id 比设置对象更高效（避免额外的 SELECT 查询），
                    #   而且 Django 会在保存时自动将 _id 写入数据库。

        super().save_model(request, obj, form, change)
        # ^ 调用父类的 save_model 执行实际的 obj.save()。
        #   必须在我们的赋值操作「之后」调用父类，
        #   这样父类保存时用的是已经被我们修正过的 bank_id，而非用户提交的值。

    # ═══════════════════════════════════════════════════════════════════════
    # 4. 对象级权限检查 — 防止通过 URL 直接访问跨行对象
    # ═══════════════════════════════════════════════════════════════════════

    def _check_object_bank(self, request, obj) -> bool:
        """
        检查给定对象是否属于当前用户所在银行。

        返回：
          True  — 对象属于本行，或当前用户是超级管理员（允许操作）
          False — 对象属于其他银行（禁止操作）

        使用场景：
          - has_change_permission / has_delete_permission / has_view_permission
          - 防止普通员工通过直接构造 URL（如 /admin/apply/bank/999/change/）访问跨行对象
        """
        if obj is None:
            # ^ obj=None 说明是列表页权限检查（非对象级），
            #   列表页的数据过滤已由 get_queryset 处理，这里直接放行。
            return True  # 列表级权限，不在此处限制

        if self._is_superuser(request):
            return True  # 超级管理员可操作任意对象

        if not self._model_has_bank_field():
            return True  # 模型无银行字段，无法判断归属，放行

        bank_id = self._get_user_bank_id(request)
        # ^ 获取当前用户所属银行主键

        if not bank_id:
            return False  # 未绑定银行，拒绝访问任何对象

        obj_bank_id = getattr(obj, f"{self.bank_field_name}_id", None)
        # ^ 获取被访问对象的银行主键。
        #   getattr 使用默认值 None 防止字段不存在时抛 AttributeError。

        return obj_bank_id == bank_id
        # ^ 比较对象的银行 id 与当前用户的银行 id。
        #   相等返回 True（同一家银行），不等返回 False（跨行访问，拒绝）。

    def has_change_permission(self, request, obj=None):
        """
        覆盖编辑权限检查。

        Django 在渲染编辑按钮、处理编辑请求前调用此方法。
        我们在父类权限基础上，额外检查对象是否属于本行。
        """
        base = super().has_change_permission(request, obj)
        # ^ 先检查父类权限（Django 的 is_staff、权限组等机制）。
        #   若父类已经禁止（返回 False），我们也应该禁止，不能越权放行。

        if not base:
            return False  # 父类已拒绝，直接返回 False，不再检查银行归属

        return self._check_object_bank(request, obj)
        # ^ 在父类允许的基础上，进一步检查银行归属。
        #   两个条件都满足才最终允许编辑。

    def has_delete_permission(self, request, obj=None):
        """
        覆盖删除权限检查。

        逻辑与 has_change_permission 相同：父类允许且同银行才允许删除。
        """
        base = super().has_delete_permission(request, obj)
        # ^ 先获取父类删除权限判断结果

        if not base:
            return False  # 父类已拒绝，直接返回

        return self._check_object_bank(request, obj)
        # ^ 银行归属检查：只能删除本行数据

    def has_view_permission(self, request, obj=None):
        """
        覆盖查看权限检查。

        防止普通员工通过直接访问详情 URL 查看其他银行的记录。
        """
        base = super().has_view_permission(request, obj)
        # ^ 先获取父类查看权限

        if not base:
            return False  # 父类已拒绝

        return self._check_object_bank(request, obj)
        # ^ 银行归属检查：只能查看本行数据

    # ═══════════════════════════════════════════════════════════════════════
    # 5. 辅助：新增时自动填充 bank 初始值（可选，提升 UX）
    # ═══════════════════════════════════════════════════════════════════════

    def get_changeform_initial_data(self, request):
        """
        覆盖 ModelAdmin.get_changeform_initial_data，为新增表单预填 bank 字段。

        调用时机：渲染新增（add）表单时，Django 调用此方法获取初始值字典。
        通过在这里返回 bank 的初始值，用户打开新增表单时 bank 字段已经预选好。

        注意：此处设置的 initial 仍可被用户修改（除非配合 get_form 的 disabled），
        真正的安全保障在 save_model 中的强制赋值。
        """
        initial = super().get_changeform_initial_data(request)
        # ^ 先获取父类的初始值字典（可能为空字典 {}，也可能包含 URL 参数值）。

        if not self._is_superuser(request):
            # ^ 只对普通员工自动填充，超级管理员不预设（让他们自由选择）。

            bank_id = self._get_user_bank_id(request)
            # ^ 获取当前用户的银行主键

            if bank_id:
                # ^ 仅在有有效银行时才填充，避免写入无效值

                initial[self.bank_field_name] = bank_id
                # ^ 将 bank 的初始值设为当前用户所属银行的主键。
                #   Django 表单会用这个主键查找对应的 Bank 实例并显示在下拉中。

        return initial  # 返回包含 bank 初始值的字典
