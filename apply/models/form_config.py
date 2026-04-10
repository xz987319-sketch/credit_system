"""表单配置模型：定义进件申请的分页结构与每页的字段配置。"""

from django.db import models


class FormPage(models.Model):
    """
    总表单页配置。

    代表进件申请表单的一个页面（Tab），
    例如基本信息、详细信息、影像采集、银行专用栏。
    order 字段配合 adminsortable2 实现拖拽排序。
    """

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="排序",
        help_text="数字越小越靠前，可通过拖拽调整顺序",
    )
    page_title = models.CharField(
        max_length=64,
        verbose_name="页面标题",
        help_text="显示在进件表单标签页上的标题",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="页面说明",
        help_text="该页面的简短说明，供内部参考",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="启用",
        help_text="关闭后该页将在进件表单中隐藏",
    )

    class Meta:
        verbose_name = "总表单页"
        verbose_name_plural = "总表单页"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.page_title


class FormField(models.Model):
    """
    子表单字段配置。

    定义某个表单页内的具体字段，
    包括字段标签、数据库存储键名、字段类型、是否必填和排序。
    """

    FIELD_TYPE_CHOICES = [
        ("text", "单行文本"),
        ("textarea", "多行文本"),
        ("select", "下拉框"),
        ("radio", "单选框"),
        ("checkbox", "复选框"),
        ("date", "日期"),
        ("number", "数字"),
        ("file", "文件上传"),
        ("image", "图片上传"),
        ("phone", "手机号"),
        ("id_card", "身份证号"),
        ("name", "姓名"),
        ("name_pinyin", "姓名拼音"),
        ("amount", "申请金额"),
    ]

    VALIDATION_RULE_CHOICES = [
        ("", "无校验"),
        ("name", "姓名校验"),
        ("id_card", "身份证号校验"),
        ("phone", "手机号校验"),
        ("amount_range", "金额区间校验"),
        ("email", "邮箱校验"),
    ]

    page = models.ForeignKey(
        FormPage,
        on_delete=models.CASCADE,
        related_name="fields",
        verbose_name="所属页面",
        help_text="该字段属于哪一个表单页",
    )
    field_label = models.CharField(
        max_length=64,
        verbose_name="字段标签",
        help_text="显示在表单中的字段名称，例如：中文姓名",
    )
    field_key = models.CharField(
        max_length=64,
        verbose_name="字段名（数据库存储键）",
        help_text="字段的唯一标识键名，例如：applicant_name",
    )
    field_type = models.CharField(
        max_length=32,
        choices=FIELD_TYPE_CHOICES,
        default="text",
        verbose_name="字段类型",
    )
    is_required = models.BooleanField(
        default=True,
        verbose_name="必填",
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="排序",
        help_text="同一页面内字段的显示顺序，数字越小越靠前",
    )
    placeholder = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="占位提示",
        help_text="输入框内的提示文字",
    )
    options = models.TextField(
        blank=True,
        default="",
        verbose_name="选项内容",
        help_text="下拉框/单选框的选项，每行一个，格式：值|显示文字",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="启用",
    )
    validation_rule = models.CharField(
        max_length=32,
        choices=VALIDATION_RULE_CHOICES,
        blank=True,
        default="",
        verbose_name="校验规则",
        help_text="选择自动应用的校验规则，如姓名、身份证、手机号、金额区间等",
    )
    max_length = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="最大长度",
        help_text="控制该字段可输入的最大字符数，不设置则不限制",
    )
    min_photos = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="最少图片张数",
        help_text="图片上传字段的最少张数要求，不设置则不限制（仅图片字段有效）",
    )
    max_photos = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name="最多图片张数",
        help_text="图片上传字段的最多张数限制，不设置则不限制（仅图片字段有效）",
    )
    is_readonly = models.BooleanField(
        default=False,
        verbose_name="置灰只读",
        help_text="开启后该字段在前端显示为灰色且不可编辑，适用于银行号等系统填充字段",
    )

    class Meta:
        verbose_name = "子表单字段"
        verbose_name_plural = "子表单字段"
        ordering = ["page__order", "sort_order"]

    def __str__(self) -> str:
        return f"{self.page} - {self.field_label}"
