"""用户模型：扩展 AbstractUser 增加银行与角色字段。"""  # 模块文档字符串
from django.contrib.auth.models import AbstractUser  # 导入可扩展的用户抽象基类
from django.db import models  # 导入字段与模型相关定义


# ── 可见菜单定义 ──────────────────────────────────────────────────────────────
# 所有可控菜单项的 key，与 settings.py UNFOLD navigation 中的菜单一一对应。
# 格式：(key, 分组, 显示名称)
MENU_ITEMS = [
    # 导航
    ("nav_home",       "导航",   "首页"),
    # 基础数据
    ("base_bank",      "基础数据", "银行"),
    ("base_user",      "基础数据", "用户"),
    ("base_card",      "基础数据", "卡产品"),
    # 业务流程
    ("biz_apply",      "业务流程", "信贷申请"),
    ("biz_audit",      "业务流程", "审核记录"),
    # 表单配置
    ("form_page",      "表单配置", "总表单页"),
    ("form_field",     "表单配置", "子表单字段"),
]


class MenuItem(models.Model):
    """
    后台菜单项，用于「后台窗口控制」双栏选择器（filter_horizontal）。
    与 settings.py UNFOLD navigation 中的菜单 key 一一对应。
    """

    key = models.CharField(max_length=64, unique=True, verbose_name="菜单标识")
    group = models.CharField(max_length=64, verbose_name="菜单分组")
    name = models.CharField(max_length=128, verbose_name="显示名称")

    class Meta:
        db_table = "apply_menu_item"
        verbose_name = "菜单项"
        verbose_name_plural = "菜单项"
        ordering = ["group", "name"]

    def __str__(self):
        return f"{self.group} / {self.name}"

    @classmethod
    def sync_from_constants(cls):
        """
        从 MENU_ITEMS 常量同步菜单项到数据库。
        迁移脚本和数据初始化时调用。
        """
        for key, group, name in MENU_ITEMS:
            cls.objects.update_or_create(key=key, defaults={"group": group, "name": name})


class User(AbstractUser):  # 定义业务用户模型继承框架用户抽象类
    """业务登录用户，支持按银行隔离与角色权限控制。"""  # 类文档字符串说明用途

    ROLE_NORMAL = "normal"  # 定义普通员工角色常量值
    ROLE_QUALITY = "quality_inspector"  # 定义银行审核员角色常量值
    ROLE_CHOICES = (  # 定义角色下拉选项元组列表
        (ROLE_NORMAL, "普通员工"),  # 普通员工中文标签
        (ROLE_QUALITY, "银行审核员"),  # 审核员中文标签
    )

    username = models.CharField(max_length=150, verbose_name="用户名")  # 重写用户名字段取消全局唯一由联合约束保证
    bank = models.ForeignKey(  # 定义用户所属银行外键可为空给超级管理员
        "apply.Bank",  # 使用字符串引用避免循环导入
        on_delete=models.PROTECT,  # 删除银行时阻止误删保护用户数据
        null=True,  # 允许为空以支持未绑定银行的超级用户
        blank=True,  # 表单校validation允许留空
        related_name="users",  # 反向查询名称为 bank.users
        verbose_name="所属银行",  # 后台字段显示名
    )
    role = models.CharField(  # 定义角色字段使用有限选项
        max_length=32,  # 足够容纳角色英文编码
        choices=ROLE_CHOICES,  # 绑定角色选项供表单与后台使用
        default=ROLE_NORMAL,  # 新建用户默认普通员工角色
        verbose_name="角色",  # 后台显示中文标签
    )
    visible_menus = models.JSONField(  # 存储该用户可见的菜单key列表（兼容旧数据）
        default=list,
        blank=True,
        verbose_name="可见窗口",
        help_text="为空时显示全部窗口；超级管理员不受此限制。",
    )
    # 后台窗口控制：通过 filter_horizontal 多选器配置，替代上述 JSONField（更友好的 UI）
    visible_menu_items = models.ManyToManyField(
        "MenuItem",
        blank=True,
        verbose_name="可见窗口",
        related_name="users",
    )

    class Meta:  # 用户模型元数据
        """设置表级约束与后台展示信息。"""  # Meta 文档字符串

        verbose_name = "用户"  # 单数后台名称
        verbose_name_plural = "用户"  # 复数后台名称
        constraints = [  # 定义数据库级约束列表
            models.UniqueConstraint(  # 创建联合唯一约束对象
                fields=["bank", "username"],  # 银行与用户名组合唯一
                name="uniq_bank_username",  # 约束名称便于迁移识别
            ),
        ]

    def __str__(self) -> str:  # 定义打印与展示字符串
        """返回用户名并附带银行号便于区分同名用户。"""  # 方法文档字符串
        code = self.bank.bank_code if self.bank_id else "SUPER"  # 无银行时显示 SUPER 表示超级用户
        return f"{code}/{self.username}"  # 拼接银行号与用户名
