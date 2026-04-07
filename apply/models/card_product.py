"""卡产品模型：描述银行可申请的信用卡产品及额度区间。"""  # 模块文档字符串
from django.db import models  # 导入模型字段定义


class CardProduct(models.Model):  # 定义卡产品实体模型
    """银行信用卡产品配置，用于 H5 下拉与额度校验。"""  # 类文档字符串

    # 基础信息
    bank = models.ForeignKey(  # 关联发行该产品的银行
        "apply.Bank",  # 延迟字符串引用 Bank 模型
        on_delete=models.CASCADE,  # 银行删除时级联删除其产品配置
        related_name="card_products",  # 反向查询 bank.card_products
        verbose_name="所属银行",  # 后台字段中文名
    )
    product_name = models.CharField(max_length=128, verbose_name="产品名称")  # 展示给用户的产品名称
    product_type = models.CharField(max_length=64, verbose_name="产品类型")  # 区分金卡白金卡等产品类型编码

    # 额度与费率
    credit_limit_min = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="最低额度")  # 可申请额度下限
    credit_limit_max = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="最高额度")  # 可申请额度上限
    annual_fee_rate = models.DecimalField(max_digits=5, decimal_places=4, verbose_name="年费率")  # 年化费率示例字段

    # 产品详情（新增字段）
    product_desc = models.TextField(  # 产品简介/描述
        blank=True, default="", verbose_name="产品简介"
    )
    product_points = models.TextField(  # 产品特点/描述
        blank=True, default="", verbose_name="产品特点"
    )
    required_docs = models.TextField(  # 产品要点/亮点
        blank=True, default="", verbose_name="产品要点"
    )
    notes = models.TextField(  # 注意事项
        blank=True, default="", verbose_name="注意事项"
    )

    # 状态控制
    is_active = models.BooleanField(default=True, verbose_name="是否启用")  # 控制是否对外展示申请

    class Meta:  # 元数据配置
        """配置 verbose 名称与默认排序。"""  # Meta 文档字符串

        verbose_name = "卡产品"  # 单数名称
        verbose_name_plural = "卡产品"  # 复数名称
        ordering = ["bank", "product_name"]  # 默认按银行与名称排序

    def __str__(self) -> str:  # 字符串表示
        """返回产品名便于管理后台选择。"""  # 方法文档字符串
        return self.product_name  # 直接返回产品名称文本
