"""日志工具模块：提供统一的文件日志和数据库日志记录功能。

支持：
- 3种日志类型：apply(进件)、admin(后台操作)、issue(发卡)
- 自动分片：每份最大5MB，超出后自动创建新文件
- 同步写入文件 + OperationLog数据库表
"""

import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from django.conf import settings


# ============================================================
# 配置
# ============================================================

MAX_FILE_SIZE = 5 * 1024 * 1024  # 每份日志最大5MB

# 日志文件存储目录（从settings读取，默认为项目根目录下的 logs 文件夹）
def get_log_dir():
    return getattr(settings, 'LOG_DIR', Path(settings.BASE_DIR) / 'logs')


# ============================================================
# 线程锁：保证多线程/多进程写入安全
# ============================================================

_file_locks = {}  # 每个日志类型一把锁
_lock_init_lock = threading.Lock()


def _get_lock(log_type: str) -> threading.Lock:
    with _lock_init_lock:
        if log_type not in _file_locks:
            _file_locks[log_type] = threading.Lock()
        return _file_locks[log_type]


# ============================================================
# 文件操作
# ============================================================

def _get_today_prefix() -> str:
    """获取当天日期前缀，如 20260410"""
    return datetime.now().strftime('%Y%m%d')


def _ensure_log_dir(log_dir: Path):
    """确保日志目录存在"""
    log_dir.mkdir(parents=True, exist_ok=True)


def _get_next_file_path(log_type: str, log_dir: Path, date_prefix: str) -> tuple[Path, int]:
    """获取下一个可用的日志文件路径，返回 (文件路径, 分片序号)

    逻辑：
    1. 检查 {date_prefix}_{log_type}.log 是否存在且未满
    2. 如果不存在或已满，查找 _1, _2, ... 顺序递增
    """
    base_name = f"{date_prefix}_{log_type}.log"

    # 检查基础文件
    base_path = log_dir / base_name
    if not base_path.exists() or base_path.stat().st_size < MAX_FILE_SIZE:
        return base_path, 0

    # 查找分片文件
    index = 1
    while True:
        shard_name = f"{date_prefix}_{index}_{log_type}.log"
        shard_path = log_dir / shard_name
        if not shard_path.exists() or shard_path.stat().st_size < MAX_FILE_SIZE:
            return shard_path, index
        index += 1


def _write_to_file(log_type: str, content: str):
    """原子性写入日志文件（线程安全）"""
    if not content.endswith('\n'):
        content += '\n'

    log_dir = get_log_dir()
    _ensure_log_dir(log_dir)
    date_prefix = _get_today_prefix()

    with _get_lock(log_type):
        file_path, shard_index = _get_next_file_path(log_type, log_dir, date_prefix)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(content)


# ============================================================
# 数据库操作
# ============================================================

def _save_to_db(log_type: str, level: str, action: str, message: str,
                user_id: Optional[int] = None, user_name: Optional[str] = None,
                target_type: Optional[str] = None, target_id: Optional[int] = None,
                extra_data: Optional[dict] = None, request=None):
    """写入 OperationLog 数据库表"""
    try:
        from apply.models.operation_log import OperationLog

        # 从request获取IP
        ip = None
        if request:
            ip = get_client_ip(request)

        OperationLog.objects.create(
            log_type=log_type,
            level=level,
            action=action,
            message=message,
            user_id=user_id,
            user_name=user_name or '',
            target_type=target_type or '',
            target_id=target_id,
            extra_data=json.dumps(extra_data, ensure_ascii=False) if extra_data else '',
            ip_address=ip or '',
        )
    except Exception:
        # 数据库写入失败不影响文件日志
        pass


def get_client_ip(request) -> str:
    """从request获取客户端IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ============================================================
# 主日志记录函数
# ============================================================

def log_apply(step_action: str, message: str,
              user_id: Optional[int] = None, user_name: Optional[str] = None,
              app_id: Optional[int] = None, form_data: Optional[dict] = None,
              request=None, extra_data: Optional[dict] = None):
    """记录进件流程日志

    Args:
        step_action: 步骤动作，如 STEP_NEXT, STEP_BACK, SUBMIT
        message: 日志消息
        user_id: 用户ID
        user_name: 用户名
        app_id: 申请ID
        form_data: 表单数据（可选，用于记录关键字段）
        request: Django请求对象（用于获取IP）
        extra_data: 额外数据
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 构建日志内容
    log_content = f"[{timestamp}] [APPLY] [{step_action}] "
    log_content += f"user_id={user_id} | user={user_name} | "
    if app_id:
        log_content += f"app_id={app_id} | "
    if form_data:
        # 只记录关键字段，避免日志过大
        key_fields = {}
        for k in ['applicant_name', 'id_card', 'phone', 'amount']:
            if k in form_data:
                key_fields[k] = form_data[k]
        log_content += f"fields={key_fields} | "
    log_content += f"msg={message}"
    if request:
        log_content += f" | ip={get_client_ip(request)}"

    # 写入文件
    _write_to_file('apply', log_content)

    # 写入数据库
    _save_to_db(
        log_type='apply',
        level='INFO',
        action=step_action,
        message=message,
        user_id=user_id,
        user_name=user_name,
        target_type='Application',
        target_id=app_id,
        extra_data=extra_data or form_data,
        request=request,
    )


def log_admin(action: str, message: str,
              user_id: Optional[int] = None, user_name: Optional[str] = None,
              target_type: Optional[str] = None, target_id: Optional[int] = None,
              before_status: Optional[str] = None, after_status: Optional[str] = None,
              request=None, extra_data: Optional[dict] = None):
    """记录后台操作日志（适用于初审、复审、信审、管理员操作）

    Args:
        action: 操作类型，如 AUDIT_PASS, AUDIT_REJECT, ISSUE_CARD, MODEL_CREATE
        message: 日志消息
        user_id: 操作人ID
        user_name: 操作人名称
        target_type: 目标类型，如 Application, FormField, User
        target_id: 目标ID
        before_status: 操作前状态（用于状态变更）
        after_status: 操作后状态
        request: Django请求对象
        extra_data: 额外数据
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 构建日志内容
    log_content = f"[{timestamp}] [ADMIN] [{action}] "
    log_content += f"operator_id={user_id} | operator={user_name} | "
    if target_type:
        log_content += f"target={target_type} | "
    if target_id:
        log_content += f"target_id={target_id} | "
    if before_status and after_status:
        log_content += f"status: {before_status} → {after_status} | "
    log_content += f"msg={message}"
    if request:
        log_content += f" | ip={get_client_ip(request)}"

    # 写入文件
    _write_to_file('admin', log_content)

    # 写入数据库
    _save_to_db(
        log_type='admin',
        level='INFO',
        action=action,
        message=message,
        user_id=user_id,
        user_name=user_name,
        target_type=target_type or '',
        target_id=target_id,
        extra_data={
            'before_status': before_status,
            'after_status': after_status,
            **(extra_data or {})
        },
        request=request,
    )


def log_issue(app_id: int, applicant_name: str, id_card: str, phone: str,
               bank_name: str, product_name: str, amount: str, issue_amount: str,
               issue_time: str, user_id: Optional[int] = None, user_name: Optional[str] = None,
               request=None, extra_data: Optional[dict] = None):
    """记录发卡信息日志（详细信息）

    Args:
        app_id: 申请ID
        applicant_name: 申请人姓名
        id_card: 身份证号
        phone: 手机号
        bank_name: 银行名称
        product_name: 卡种名称
        amount: 申请额度
        issue_amount: 实际发卡额度
        issue_time: 发卡时间
        user_id: 操作人ID（超级管理员）
        user_name: 操作人名称
        request: Django请求对象
        extra_data: 额外数据
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 构建日志内容（格式化的详细信息）
    lines = [
        f"[{timestamp}] [ISSUE] ======================================",
        f"[{timestamp}] [ISSUE] 发卡记录 - 申请ID: {app_id}",
        f"[{timestamp}] [ISSUE] 申请人: {applicant_name}",
        f"[{timestamp}] [ISSUE] 身份证: {id_card}",
        f"[{timestamp}] [ISSUE] 手机号: {phone}",
        f"[{timestamp}] [ISSUE] 所属银行: {bank_name}",
        f"[{timestamp}] [ISSUE] 申请卡种: {product_name}",
        f"[{timestamp}] [ISSUE] 申请额度: {amount}",
        f"[{timestamp}] [ISSUE] 实际发卡额度: {issue_amount}",
        f"[{timestamp}] [ISSUE] 发卡时间: {issue_time}",
        f"[{timestamp}] [ISSUE] 操作人: {user_name} (ID: {user_id})",
        f"[{timestamp}] [ISSUE] ======================================",
    ]

    log_content = '\n'.join(lines)

    # 写入文件
    _write_to_file('issue', log_content)

    # 写入数据库
    _save_to_db(
        log_type='issue',
        level='INFO',
        action='ISSUE_CARD',
        message=f"发卡成功 - 申请人:{applicant_name} - 额度:{issue_amount}",
        user_id=user_id,
        user_name=user_name,
        target_type='Application',
        target_id=app_id,
        extra_data={
            'applicant_name': applicant_name,
            'id_card': id_card,
            'phone': phone,
            'bank_name': bank_name,
            'product_name': product_name,
            'amount': amount,
            'issue_amount': issue_amount,
            'issue_time': issue_time,
            **(extra_data or {})
        },
        request=request,
    )
