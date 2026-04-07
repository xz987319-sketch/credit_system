"""表单定义：登录、H5 进件、补充资料与各类拒绝原因录入。"""  # 模块文档字符串

from django import forms  # 导入表单基类与字段构造器

from apply.models import Application, Bank, CardProduct  # 导入申请、卡产品与银行模型
from apply.utils.applicant_validate import (  # 导入姓名证件手机号校验函数
    clean_applicant_name,  # 姓名规则
    clean_cn_mobile,  # 手机号
    clean_id_card_18,  # 18 位身份证
)
from apply.utils.apply_duplicate import id_card_holds_card_product  # 导入证件卡种防重判断
from apply.utils.amount_validate import (  # 导入金额字符串服务端校验
    resolve_card_product_from_post,  # 从 POST 解析卡种
    validate_submitted_amount_string,  # 校验金额文本
)
from apply.widgets import CardProductLimitsSelect  # 导入带 data 区间的卡种下拉控件


class CardProductModelChoiceField(forms.ModelChoiceField):  # 自定义卡种下拉显示标签
    """将下拉选项标签显示为产品名称便于用户理解。"""  # 类文档字符串

    def __init__(self, *args, **kwargs):  # 构造函数确保默认 widget 可在外部覆盖
        """若未传入 widget 则使用 Bootstrap 下拉样式。"""  # 文档字符串
        if "widget" not in kwargs:  # 未显式指定控件时
            kwargs["widget"] = forms.Select(attrs={"class": "form-select"})  # 应用默认样式
        super().__init__(*args, **kwargs)  # 调用父类完成初始化

    def label_from_instance(self, obj: CardProduct) -> str:  # 重写实例到标签转换
        """返回产品名称作为选项文本。"""  # 方法文档字符串
        return obj.product_name  # 直接展示产品名称


class LoginForm(forms.Form):  # 定义登录页使用的非模型表单
    """收集银行号、用户名、密码与用户输入的验证码。"""  # 类文档字符串

    _login_input = {"class": "form-control login-input"}  # 登录页输入框统一样式类名
    bank_code = forms.CharField(  # 银行号
        label="银行号",  # 标签
        max_length=16,  # 长度
        widget=forms.TextInput(attrs={**_login_input, "placeholder": "", "autocomplete": "organization"}),  # 控件属性
    )
    username = forms.CharField(  # 用户名
        label="用户名",  # 标签
        max_length=150,  # 长度
        widget=forms.TextInput(attrs={**_login_input, "autocomplete": "username"}),  # 浏览器可记住用户名
    )
    password = forms.CharField(  # 密码
        label="密码",  # 标签
        widget=forms.PasswordInput(attrs={**_login_input, "autocomplete": "current-password"}),  # 密码框
    )
    captcha = forms.CharField(  # 验证码（左侧输入，右侧可点击刷新区由模板渲染）
        label="验证码",  # 标签
        max_length=16,  # 长度
        widget=forms.TextInput(  # 文本输入
            attrs={  # 属性
                **{k: v for k, v in _login_input.items()},  # 继承 login-input
                "placeholder": "请输入验证码",  # 占位
                "autocomplete": "off",  # 关闭自动填充
                "id": "id_captcha_input",  # 固定 id 供刷新后清空脚本使用
            },
        ),
    )


class H5ApplyForm(forms.ModelForm):  # 定义 H5 匿名申请表单继承模型表单
    """映射申请模型字段并增加额度与证件格式校验逻辑。"""  # 类文档字符串

    amount = forms.CharField(  # 使用文本框收集金额，便于前端精细控制输入
        label="申请金额（元）",  # 字段标签
        required=True,  # 必填
        widget=forms.TextInput(  # 使用 text 而非 number，避免上下箭头
            attrs={  # HTML 属性
                "class": "form-control apply-amount-input",  # 样式与脚本钩子
                "inputmode": "decimal",  # 移动端弹出数字键盘
                "autocomplete": "off",  # 关闭自动完成减少干扰
                "placeholder": "请输入申请金额",  # 占位提示
            },
        ),
    )

    class Meta:  # 先声明 Meta 供父类识别模型字段
        """指定模型与字段并统一控件样式。"""  # Meta 文档字符串

        model = Application  # 绑定信贷申请模型
        fields = ["applicant_name", "id_card", "phone", "card_product", "amount"]  # 客户可填字段
        widgets = {  # 为各字段指定 Bootstrap 表单控件类
            "applicant_name": forms.TextInput(attrs={"class": "form-control"}),  # 姓名
            "id_card": forms.TextInput(attrs={"class": "form-control"}),  # 身份证
            "phone": forms.TextInput(attrs={"class": "form-control"}),  # 手机
        }

    def __init__(self, *args, card_queryset=None, **kwargs):  # 构造函数接收卡产品查询集
        """用演示银行的启用产品填充卡种下拉选项。"""  # 方法文档字符串
        super().__init__(*args, **kwargs)  # 调用父类初始化生成默认字段
        qs = card_queryset if card_queryset is not None else CardProduct.objects.none()  # 缺省使用空查询集避免误展示
        self.fields["card_product"] = CardProductModelChoiceField(  # 替换为自定义下拉字段
            queryset=qs,  # 绑定外部传入的受限查询集
            required=True,  # 要求必须选择卡种
            label="申请卡种",  # 设置字段标签
            widget=CardProductLimitsSelect(attrs={"class": "form-select"}),  # 带额度 data 的下拉
        )

    def clean_applicant_name(self):  # 清洗申请人姓名字段
        """仅允许汉字与少数民族用「·」，长度 1～15。"""  # 方法文档字符串
        value = self.cleaned_data.get("applicant_name", "")  # 读取原始输入
        return clean_applicant_name(value)  # 委托工具函数（异常直接向上抛出）

    def clean_id_card(self):  # 清洗身份证号字段
        """按业务正则校验 18 位身份证并规范末位 X。"""  # 方法文档字符串
        value = self.cleaned_data.get("id_card", "")  # 取出身份证字符串
        return clean_id_card_18(value)  # 委托身份证校验工具

    def clean_phone(self):  # 清洗手机号字段
        """校验中国大陆手机号号段与长度。"""  # 方法文档字符串
        value = self.cleaned_data.get("phone", "")  # 取出手机号
        return clean_cn_mobile(value)  # 委托手机号校验工具

    def clean_amount(self):  # 清洗申请金额文本
        """将文本解析为 Decimal 并按所选卡种校验区间（防前端绕过）。"""  # 方法文档字符串
        raw = self.cleaned_data.get("amount", "")  # 取出用户输入字符串
        product = self.cleaned_data.get("card_product")  # 优先用已校验通过的卡种对象
        if product is None:  # 若卡种字段校验失败或未选
            product = resolve_card_product_from_post(self.data, "card_product")  # 尝试从原始 POST 解析
        return validate_submitted_amount_string(raw, product)  # 统一服务端规则并返回 Decimal

    def clean(self):  # 表单级联合校验
        """校验同一证件号对同一卡种不可重复有效申请（金额在 clean_amount 已处理）。"""  # 方法文档字符串
        cleaned = super().clean()  # 先执行父类清洗获取基础字典
        product = cleaned.get("card_product")  # 读取卡产品对象
        amount = cleaned.get("amount")  # 读取 Decimal 额度
        id_card_val = cleaned.get("id_card")  # 读取已规范化的身份证号
        if id_card_val and product and amount is not None:  # 三者齐全时再查重
            if id_card_holds_card_product(id_card_val, product.pk, exclude_pk=None):  # 新建进件不排除主键
                raise forms.ValidationError("您已拥有该卡种，不可重复申请")  # 业务防重提示
        return cleaned  # 返回清洗后的数据字典


class ReturnEditForm(forms.ModelForm):  # 定义退回后补充资料编辑表单
    """允许修改补充说明。姓名、身份证、手机、卡种、金额不可编辑。"""  # 类文档字符串

    class Meta:  # 元类绑定字段与样式
        """绑定需要编辑的模型字段列表。"""  # Meta 文档字符串

        model = Application  # 使用申请模型
        fields = [  # 指定可编辑字段（核心信息不可编辑）
            "supplementary_note",  # 补充说明
        ]
        widgets = {  # 控件样式映射
            "supplementary_note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),  # 补充说明
        }

    def __init__(self, *args, card_queryset=None, **kwargs):  # 构造函数支持传入卡产品集合
        """限制卡种下拉仅展示本行启用产品。"""  # 方法文档字符串
        super().__init__(*args, **kwargs)  # 执行父类初始化


class ReasonForm(forms.Form):  # 通用原因输入表单
    """单行或多行文本记录审批拒绝或退回原因。"""  # 类文档字符串

    reason = forms.CharField(  # 原因字段定义
        label="原因说明",  # 显示标签
        min_length=2,  # 最短长度防止空泛输入
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),  # 文本域样式
    )


# =============================================================================
# 员工申请表单：登录用户只能为自己的银行创建申请
# =============================================================================
# 设计思路：
#   - 普通员工（已登录）可以在前台为自己的银行创建信用卡申请单
#   - 每个员工通过 User.bank 字段绑定到具体的银行（如 0011、0022）
#   - 员工只能选择自己银行发行的卡产品（CardProduct.bank = User.bank）
#   - 后端在 clean() 中再次校验卡种是否属于当前用户的银行，防止前端绕过
#
# 与 H5ApplyForm 的区别：
#   - H5ApplyForm：匿名用户，只能选演示银行（0000），无需 bank 字段
#   - EmployeeApplyForm：登录用户，只能选自己银行的产品，有 bank 字段
# =============================================================================

class EmployeeApplyForm(forms.ModelForm):
    """
    员工登录后使用的信用卡申请表单。

    核心防护机制：
    1. bank 字段由后端根据 request.user.bank 自动确定，前端无法伪造
    2. card_product 下拉框仅展示当前用户银行的启用卡产品
    3. clean() 中二次校验所选卡种必须属于当前用户的银行
    """

    # -------------------------------------------------------------------------
    # amount 字段：使用 CharField 而非 DecimalField，让用户输入"万元"格式文本，
    # 由 clean_amount() 解析并校验是否在所选卡种的允许额度区间内。
    # -------------------------------------------------------------------------
    amount = forms.CharField(
        label="申请金额（元）",  # 表单标签文字
        required=True,  # 必填字段
        widget=forms.TextInput(  # 使用文本框避免移动端 number 上下箭头
            attrs={  # HTML 属性字典
                "class": "form-control apply-amount-input",  # Bootstrap 样式类
                "inputmode": "decimal",  # 触发移动端数字键盘（含小数点）
                "autocomplete": "off",  # 关闭浏览器自动填充
                "placeholder": "请输入申请金额",  # 输入前占位提示
            },
        ),
    )

    class Meta:
        """
        指定表单关联的模型、暴露的字段和默认控件样式。

        注意：bank 字段不在 fields 列表中，因为我们不希望用户在前端选择银行，
        银行由后端根据 request.user.bank 自动填充（见 __init__）。
        """
        model = Application  # 绑定信贷申请模型
        fields = [  # 表单可见字段列表
            "applicant_name",  # 申请人姓名
            "id_card",  # 身份证号
            "phone",  # 手机号
            "card_product",  # 申请卡种
            # "bank" 不在 fields 中：银行由后端自动设置，前端不可选
        ]
        widgets = {  # 为各字段指定 Bootstrap 控件样式
            "applicant_name": forms.TextInput(attrs={"class": "form-control"}),  # 姓名输入框
            "id_card": forms.TextInput(attrs={"class": "form-control"}),  # 身份证输入框
            "phone": forms.TextInput(attrs={"class": "form-control"}),  # 手机输入框
        }

    def __init__(self, *args, user_bank=None, card_queryset=None, **kwargs):
        """
        构造函数：注入当前用户的银行和受限的卡产品查询集。

        参数说明：
        - user_bank：当前登录用户的 Bank 实例（或 None）。用于生成 bank 字段
          标签、预填充只读字段，以及后端校验。
        - card_queryset：经过银行过滤后的 CardProduct 查询集。
          调用方（视图）应已根据 user_bank 过滤好，仅包含本行产品。

        为什么用 deepcopy？因为 form.fields 是类属性，若直接修改会污染同类的
        其他实例。使用 deepcopy 确保每个表单实例有独立的字段副本。
        """
        # 调用父类构造函数，生成基础字段和 cleaned_data 框架
        super().__init__(*args, **kwargs)

        # -------------------------------------------------------------------------
        # 处理 bank 字段：展示当前用户的银行信息，但设为只读（不可在前端修改）
        # -------------------------------------------------------------------------
        if user_bank is not None:
            # 第1步：把 bank 外键加入 fields，让 Django 保存时能写入 bank_id
            self.fields["bank"] = forms.ModelChoiceField(
                queryset=Bank.objects.filter(pk=user_bank.pk),  # 下拉只有本行一个选项
                initial=user_bank.pk,  # 设置初始值为本行银行
                widget=forms.TextInput(attrs={"readonly": "readonly", "class": "form-control"}),  # 只读文本框
                label="所属银行",  # 表单标签
                required=True,  # 必填（但前端不可改）
            )
            # 第2步：将 bank 字段追加到 fields 列表（Meta.fields 中没有）
            self.fields["bank"].initial = user_bank.pk  # 双重保险：确保初始值为本行

        # -------------------------------------------------------------------------
        # 处理 card_product 字段：用自定义下拉字段替换，并绑定受限的 queryset
        # -------------------------------------------------------------------------
        if card_queryset is not None:
            # CardProductModelChoiceField.label_from_instance 会返回 product_name
            # 作为选项文本，比默认显示"CardProduct object (1)"更友好
            self.fields["card_product"] = CardProductModelChoiceField(
                queryset=card_queryset,  # 受限查询集：仅当前用户银行的启用产品
                required=True,  # 必须选择一个卡种
                label="申请卡种",  # 表单标签
                widget=CardProductLimitsSelect(attrs={"class": "form-select"}),  # 带额度区间的下拉
            )

    def clean_applicant_name(self):
        """
        姓名字段清洗：仅允许汉字和少数民族用字点，长度 1～15。

        调用时机：is_valid() 时自动触发，校验失败则表单报错。
        """
        value = self.cleaned_data.get("applicant_name", "")  # 读取原始输入字符串
        return clean_applicant_name(value)  # 委托工具函数，异常向上抛出

    def clean_id_card(self):
        """
        身份证字段清洗：校验 18 位身份证号格式，并规范末位大小写。

        调用时机：is_valid() 时在 clean_applicant_name 之后自动触发。
        """
        value = self.cleaned_data.get("id_card", "")  # 取出已去除首尾空白的字符串
        return clean_id_card_18(value)  # 委托工具函数处理格式校验

    def clean_phone(self):
        """
        手机号字段清洗：校验中国大陆手机号号段和长度（11 位）。

        调用时机：is_valid() 时在 clean_id_card 之后自动触发。
        """
        value = self.cleaned_data.get("phone", "")  # 取出手机号字符串
        return clean_cn_mobile(value)  # 委托工具函数，异常向上抛出

    def clean_amount(self):
        """
        金额字段清洗：解析用户输入的文本为 Decimal，并校验是否在卡种允许区间。

        参数说明：
        - raw：用户在 amount 字段输入的字符串（如"50000"或"5万元"）
        - product：card_product 字段的对象引用，用于获取 min_limit / max_limit

        为什么优先用 cleaned_data？因为 is_valid() 依次执行各字段的 clean_xxx，
        此时 card_product 已经校验通过（存在于数据库），可以从 cleaned_data 获取。
        若 card_product 校验失败（如非法 pk），则从原始 POST 数据解析（兜底逻辑）。
        """
        raw = self.cleaned_data.get("amount", "")  # 取出用户输入的原始字符串
        product = self.cleaned_data.get("card_product")  # 获取已校验的卡种对象

        # 若 card_product 字段校验失败（不存在或非法），尝试从原始 POST 数据解析
        # 这是一种兜底逻辑，防止卡种字段报错时金额也无法提交
        if product is None:
            product = resolve_card_product_from_post(self.data, "card_product")

        # 统一调用工具函数：解析文本并按卡种额度区间校验，返回 Decimal 或抛异常
        return validate_submitted_amount_string(raw, product)

    def clean(self):
        """
        表单级联合校验（clean 方法链的最后一环）。

        这里做最重要的安全校验：确保用户选择的卡种属于其所属银行。

        为什么需要这步？因为即使前端下拉框只展示了本行卡产品，
        恶意用户仍然可以通过拦截请求、修改 POST 数据中的 card_product 值，
        尝试为其他银行的产品提交申请。clean() 中的这步校验是最后一道防线。

        调用时机：所有字段的 clean_xxx 完成后、is_valid() 返回 True 之前触发。
        """
        # 第1步：先执行父类 clean()，获取各字段清洗后的数据字典
        cleaned = super().clean()

        # 第2步：提取 card_product（卡种）和 user_bank（用户银行）
        product = cleaned.get("card_product")  # CardProduct 实例（或 None）
        user_bank = cleaned.get("bank")  # Bank 实例（或 None）

        # 第3步：提取用户输入的身份证号（用于防重判断）
        id_card_val = cleaned.get("id_card")

        # -------------------------------------------------------------------------
        # 安全校验 1：卡种必须属于用户的银行
        # -------------------------------------------------------------------------
        if product is not None and user_bank is not None:
            # 比较卡产品的银行 ID 和当前用户的银行 ID 是否一致
            if product.bank_id != user_bank.pk:
                # 不一致时，说明用户尝试通过修改 POST 绕过前端限制
                # 抛出 ValidationError 使 is_valid() 返回 False
                raise forms.ValidationError(
                    # 错误信息会显示在表单非字段错误中（non_field_errors）
                    "您没有权限为该银行提交申请，请刷新页面重试。",
                    code="card_product_bank_mismatch",
                )

        # -------------------------------------------------------------------------
        # 安全校验 2：同一身份证对同一卡种不可重复申请（业务防重）
        # -------------------------------------------------------------------------
        # 只有当身份证、卡种、金额三个关键字段都存在时才执行查重逻辑
        amount = cleaned.get("amount")  # Decimal 额度（或 None）
        if id_card_val and product and amount is not None:
            # 调用工具函数判断该证件是否已持有该卡种的有效申请
            # exclude_pk=None 表示新建进件，不排除任何主键（查全部历史记录）
            if id_card_holds_card_product(id_card_val, product.pk, exclude_pk=None):
                raise forms.ValidationError("您已拥有该卡种，不可重复申请")

        # -------------------------------------------------------------------------
        # 返回清洗后的完整数据字典，供 save() 使用
        # 注意：此时 bank 字段已经是 Bank 实例，保存时会写入 bank_id
        # -------------------------------------------------------------------------
        return cleaned
