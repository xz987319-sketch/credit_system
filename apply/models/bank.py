"""银行模型：存储多银行隔离所需的机构编码与名称。"""  # 模块文档字符串说明模型职责
from django.db import models  # 导入模型基类与字段定义工具


# ── 品牌色预设列表 ────────────────────────────────────────────────────────────
# 每项：(hex值, 中文名称)，供 brand_color choices 下拉使用。
BRAND_COLOR_CHOICES = [
    ("#3182ce", "蓝色"),
    ("#2196f3", "亮蓝色"),
    ("#03a9f4", "浅蓝色"),
    ("#00bcd4", "青色"),
    ("#009688", "青绿色"),
    ("#27ae60", "绿色"),
    ("#4caf50", "亮绿色"),
    ("#8bc34a", "浅绿色"),
    ("#cddc39", "黄绿色"),
    ("#ffeb3b", "黄色"),
    ("#ffc107", "琥珀色"),
    ("#ff9800", "橙色"),
    ("#ff5722", "深橙色"),
    ("#e74c3c", "红色"),
    ("#c0392b", "深红色"),
    ("#e91e63", "粉红色"),
    ("#9c27b0", "紫色"),
    ("#9b59b6", "淡紫色"),
    ("#673ab7", "深紫色"),
    ("#3f51b5", "靛蓝色"),
    ("#607d8b", "蓝灰色"),
    ("#795548", "棕色"),
    ("#9e9e9e", "灰色"),
    ("#000000", "黑色"),
]


class Bank(models.Model):  # 定义银行实体模型继承 Model
    """表示一家银行机构，用于与用户和申请数据关联实现隔离。"""  # 类文档字符串

    bank_code = models.CharField(max_length=16, unique=True, verbose_name="银行号")  # 唯一银行编码用于登录与关联
    bank_name = models.CharField(max_length=128, verbose_name="银行名称")  # 展示用银行中文名称
    brand_color = models.CharField(
        max_length=7,
        choices=BRAND_COLOR_CHOICES,
        default="#3182ce",
        verbose_name="品牌色",
        help_text="选择银行品牌色，将用于卡片与界面展示。",
    )  # 品牌色：下拉选择，存 hex 值，显示中文名称
    is_featured = models.BooleanField(default=False, verbose_name="热门银行")  # 是否展示在热门银行

    class Meta:  # 元数据配置内部类
        """配置数据库表名与后台展示名称。"""  # Meta 文档字符串

        verbose_name = "银行"  # 单数形式后台显示名
        verbose_name_plural = "银行"  # 复数形式后台显示名
        ordering = ["-is_featured", "bank_code"]  # 热门银行优先显示

    def __str__(self) -> str:  # 定义对象字符串表示
        """返回银行号与名称组合便于下拉与日志识别。"""  # 方法文档字符串
        return f"{self.bank_code} {self.bank_name}"  # 拼接编码与名称返回可读文本
    
    def get_active_products(self):
        """获取该银行所有启用中的卡产品。"""
        return self.card_products.filter(is_active=True)
    
    def get_featured_products(self, limit=2):
        """获取该银行推荐的热门卡片。"""
        return self.card_products.filter(is_active=True)[:limit]
