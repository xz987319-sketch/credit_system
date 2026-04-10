"""操作日志模型：记录所有业务操作日志，支持后台查询。"""

from django.db import models


class OperationLog(models.Model):
    """操作日志表

    记录所有业务操作的详细日志，包括进件流程、后台审核、系统配置等。
    日志同时写入文件（见 apply/utils/logger.py），本表用于后台管理查询。
    """

    LOG_TYPE_CHOICES = [
        ('apply', '进件流程'),
        ('admin', '后台操作'),
        ('issue', '发卡信息'),
    ]

    LEVEL_CHOICES = [
        ('DEBUG', '调试'),
        ('INFO', '信息'),
        ('WARNING', '警告'),
        ('ERROR', '错误'),
    ]

    # 日志基本信息
    log_type = models.CharField(
        max_length=20,
        choices=LOG_TYPE_CHOICES,
        default='admin',
        verbose_name='日志类型',
        db_index=True,
    )
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='INFO',
        verbose_name='日志级别',
    )
    action = models.CharField(
        max_length=100,
        verbose_name='操作类型',
        db_index=True,
    )
    message = models.TextField(
        verbose_name='日志消息',
    )

    # 操作人信息
    user_id = models.IntegerField(
        null=True, blank=True,
        verbose_name='操作人ID',
        db_index=True,
    )
    user_name = models.CharField(
        max_length=150,
        default='',
        blank=True,
        verbose_name='操作人姓名',
    )

    # 操作对象信息
    target_type = models.CharField(
        max_length=100,
        default='',
        blank=True,
        verbose_name='目标类型',
        db_index=True,
    )
    target_id = models.IntegerField(
        null=True, blank=True,
        verbose_name='目标ID',
        db_index=True,
    )

    # 状态变更（用于审核流程）
    before_status = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name='操作前状态',
    )
    after_status = models.CharField(
        max_length=50,
        default='',
        blank=True,
        verbose_name='操作后状态',
    )

    # 额外数据（JSON格式）
    extra_data = models.TextField(
        default='',
        blank=True,
        verbose_name='额外数据(JSON)',
    )

    # 访问信息
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name='IP地址',
    )

    # 时间戳
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_index=True,
    )

    class Meta:
        db_table = 'apply_operation_log'
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-created_at']  # 默认按时间倒序
        indexes = [
            models.Index(fields=['log_type', 'created_at']),
            models.Index(fields=['user_id', 'created_at']),
            models.Index(fields=['target_type', 'target_id']),
        ]

    def __str__(self):
        return f"[{self.log_type}] {self.action} - {self.message[:50]}"

    @classmethod
    def get_type_name(cls, log_type: str) -> str:
        """获取日志类型中文名"""
        return dict(cls.LOG_TYPE_CHOICES).get(log_type, log_type)
