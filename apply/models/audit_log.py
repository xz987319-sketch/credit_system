"""审计日志模型：可选记录审批动作便于扩展演示。"""  # 模块文档字符串
from django.conf import settings  # 导入设置获取用户模型路径
from django.db import models  # 导入模型定义工具


class AuditLog(models.Model):  # 定义审计日志表结构
    """记录对申请单的一次审批动作及意见文本。"""  # 类文档字符串说明用途

    application = models.ForeignKey(  # 关联被操作的申请单
        "apply.Application",  # 引用申请模型
        on_delete=models.CASCADE,  # 申请删除时清理其日志
        related_name="audit_logs",  # 反向 application.audit_logs
        verbose_name="申请单",  # 后台显示名
    )
    auditor = models.ForeignKey(  # 记录操作人
        settings.AUTH_USER_MODEL,  # 使用自定义用户模型
        on_delete=models.SET_NULL,  # 用户删除保留日志
        null=True,  # 允许为空兼容历史数据
        related_name="audit_logs",  # 反向 user.audit_logs
        verbose_name="审批人",  # 后台显示名
    )
    result = models.CharField(max_length=64, verbose_name="结果")  # 简要结果编码或文本
    comment = models.TextField(blank=True, default="", verbose_name="意见")  # 详细审批意见
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="记录时间")  # 自动写入创建时间

    class Meta:  # 元数据
        """配置展示名称与排序。"""  # Meta 文档字符串

        verbose_name = "审计日志"  # 单数名称
        verbose_name_plural = "审计日志"  # 复数名称
        ordering = ["-created_at"]  # 最新记录优先展示

    def __str__(self) -> str:  # 字符串表示
        """返回申请主键与结果摘要。"""  # 方法文档字符串
        return f"申请{self.application_id}:{self.result}"  # 简短描述日志条目
