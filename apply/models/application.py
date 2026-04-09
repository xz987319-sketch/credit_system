"""申请模型：记录客户信贷进件全生命周期状态与发卡信息。"""  # 模块文档字符串
from django.conf import settings  # 导入 settings 以引用 AUTH_USER_MODEL
from django.db import models  # 导入 ORM 字段与模型基类


class Application(models.Model):  # 定义信贷申请业务主表
    """单笔信贷申请从进件到发卡或拒绝的完整数据载体。"""  # 类文档字符串

    ST_PENDING_FIRST = "pending_first"  # 待初审状态常量
    ST_FIRST_PASS = "first_pass"  # 初审通过中间态常量（流程可扩展预留）
    ST_FIRST_REJECT = "first_reject"  # 初审拒绝状态常量
    ST_PENDING_SECOND = "pending_second"  # 待复审状态常量
    ST_SECOND_PASS = "second_pass"  # 复审通过中间态常量
    ST_SECOND_REJECT = "second_reject"  # 复审拒绝终止态常量
    ST_CREDIT_ING = "credit_ing"  # 信审中状态常量
    ST_ISSUED = "issued"  # 已发卡完成态常量
    ST_REJECTED = "rejected"  # 信审拒绝终止态常量
    ST_RETURNED = "returned"  # 退回补充资料状态常量
    STATUS_CHOICES = (  # 状态枚举供表单与后台使用
        (ST_PENDING_FIRST, "待初审"),  # 待初审中文描述
        (ST_FIRST_PASS, "初审通过"),  # 初审通过中文描述
        (ST_FIRST_REJECT, "初审拒绝"),  # 初审拒绝中文描述
        (ST_PENDING_SECOND, "待复审"),  # 待复审中文描述
        (ST_SECOND_PASS, "复审通过"),  # 复审通过中文描述
        (ST_SECOND_REJECT, "复审拒绝"),  # 复审拒绝中文描述
        (ST_CREDIT_ING, "信审中"),  # 信审中文描述
        (ST_ISSUED, "已发卡"),  # 已发卡中文描述
        (ST_REJECTED, "信审拒绝"),  # 信审拒绝中文描述
        (ST_RETURNED, "退回补充"),  # 退回补充中文描述
    )

    user = models.ForeignKey(  # 可选关联内部员工账号
        settings.AUTH_USER_MODEL,  # 使用配置中的用户模型避免硬编码
        on_delete=models.SET_NULL,  # 员工删除时保留申请记录
        null=True,  # 允许为空支持 H5 匿名进件
        blank=True,  # 表单允许不选员工
        related_name="applications",  # 反向 user.applications
        verbose_name="关联员工",  # 后台显示名
    )
    bank = models.ForeignKey(  # 申请所属银行用于数据隔离
        "apply.Bank",  # 引用 Bank 模型
        on_delete=models.PROTECT,  # 防止删除银行破坏历史数据
        related_name="applications",  # 反向 bank.applications
        verbose_name="所属银行",  # 后台显示名
    )
    card_product = models.ForeignKey(  # 客户选择的卡产品
        "apply.CardProduct",  # 引用卡产品模型
        on_delete=models.PROTECT,  # 防止删除产品破坏历史
        related_name="applications",  # 反向查询
        verbose_name="申请卡种",  # 后台显示名
    )
    applicant_name = models.CharField(max_length=64, verbose_name="申请人姓名")  # 客户姓名
    id_card = models.CharField(max_length=18, verbose_name="身份证号")  # 18 位身份证号码
    phone = models.CharField(max_length=11, verbose_name="手机号")  # 11 位手机号
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="申请额度")  # 申请金额元
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=ST_PENDING_FIRST, verbose_name="状态")  # 流程状态
    card_number = models.CharField(max_length=32, blank=True, default="", verbose_name="虚拟卡号")  # 发卡后写入虚拟卡号
    return_reason = models.TextField(blank=True, default="", verbose_name="退回原因")  # 初审退回说明
    supplementary_note = models.TextField(blank=True, default="", verbose_name="补充说明")  # 客户补充说明
    init_audit_time = models.DateTimeField(null=True, blank=True, verbose_name="初审通过时间")  # 初审通过时刻
    second_audit_time = models.DateTimeField(null=True, blank=True, verbose_name="复审通过时间")  # 复审通过时刻
    credit_audit_time = models.DateTimeField(null=True, blank=True, verbose_name="信审通过时间")  # 信审通过时刻
    issued_time = models.DateTimeField(null=True, blank=True, verbose_name="已发卡时间")  # 已发卡时刻
    credit_time = models.DateTimeField(null=True, blank=True, verbose_name="信审结束时间")  # 信审结束时刻（通过或拒绝）
    credit_remark = models.TextField(blank=True, default="", verbose_name="信审备注")  # 仅记录信审拒绝等原因
    second_reject_reason = models.TextField(blank=True, default="", verbose_name="复审拒绝原因")  # 复审拒绝专用说明
    issue_data = models.JSONField(null=True, blank=True, verbose_name="发卡快照")  # 发卡 JSON 快照用于比对
    form_data = models.JSONField(null=True, blank=True, verbose_name="动态表单数据")  # 多步骤表单数据存储
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")  # 记录创建时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")  # 每次保存自动更新

    class Meta:  # 申请模型元数据
        """配置 verbose 与默认排序。"""  # Meta 文档字符串

        verbose_name = "信贷申请"  # 单数名称
        verbose_name_plural = "信贷申请"  # 复数名称
        ordering = ["-created_at"]  # 默认最新申请在前

    def __str__(self) -> str:  # 对象字符串
        """返回主键与申请人姓名组合标识。"""  # 方法文档字符串
        return f"#{self.pk} {self.applicant_name}"  # 拼接编号与姓名
