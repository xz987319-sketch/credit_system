"""Admin CRUD 信号监听：自动记录模型的新增、修改、删除操作。

支持记录以下模型的变更：
- User (用户)
- Bank (银行)
- CardProduct (卡产品)
- FormPage (表单页)
- FormField (表单字段)
- MenuItem (菜单项)
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apply.models import User, Bank, CardProduct
from apply.models.form_config import FormPage, FormField
from apply.models.user import MenuItem


# 需要记录的模型列表
TRACKED_MODELS = {
    User: 'User',
    Bank: 'Bank',
    CardProduct: 'CardProduct',
    FormPage: 'FormPage',
    FormField: 'FormField',
    MenuItem: 'MenuItem',
}


def _get_user_info(request=None):
    """从当前请求或线程局部变量获取用户信息"""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from threading import local
        _thread_locals = local()
        user = getattr(_thread_locals, 'current_user', None)
        if user:
            return user.id, user.username
    except Exception:
        pass
    return None, 'system'


def _get_request_from_thread():
    """从线程局部变量获取请求对象"""
    try:
        from threading import local
        _thread_locals = local()
        return getattr(_thread_locals, 'current_request', None)
    except Exception:
        return None


def _safe_log(action, model_name, pk, changes=None):
    """安全记录日志，失败不抛异常"""
    try:
        from apply.utils.logger import log_admin
        user_id, user_name = _get_user_info()
        request = _get_request_from_thread()

        message = f'{model_name}'
        if action == 'CREATE':
            message = f'新建 {model_name}'
        elif action == 'UPDATE':
            message = f'更新 {model_name}'
            if changes:
                field_names = list(changes.keys()) if isinstance(changes, dict) else str(changes)
                message += f'，修改字段: {field_names}'
        elif action == 'DELETE':
            message = f'删除 {model_name}'

        log_admin(
            action=action,
            message=message,
            user_id=user_id,
            user_name=user_name,
            target_type=model_name,
            target_id=pk,
            request=request,
        )
    except Exception:
        pass


# ============================================================
# User 信号
# ============================================================

@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created:
        _safe_log('CREATE', 'User', instance.pk)
    else:
        # 检查是否有实际变更
        update_fields = kwargs.get('update_fields')
        if update_fields:
            _safe_log('UPDATE', 'User', instance.pk, changes=list(update_fields))
        else:
            _safe_log('UPDATE', 'User', instance.pk)


@receiver(post_delete, sender=User)
def user_post_delete(sender, instance, **kwargs):
    _safe_log('DELETE', 'User', instance.pk)


# ============================================================
# Bank 信号
# ============================================================

@receiver(post_save, sender=Bank)
def bank_post_save(sender, instance, created, **kwargs):
    if created:
        _safe_log('CREATE', 'Bank', instance.pk)
    else:
        update_fields = kwargs.get('update_fields')
        if update_fields:
            _safe_log('UPDATE', 'Bank', instance.pk, changes=list(update_fields))
        else:
            _safe_log('UPDATE', 'Bank', instance.pk)


@receiver(post_delete, sender=Bank)
def bank_post_delete(sender, instance, **kwargs):
    _safe_log('DELETE', 'Bank', instance.pk)


# ============================================================
# CardProduct 信号
# ============================================================

@receiver(post_save, sender=CardProduct)
def cardproduct_post_save(sender, instance, created, **kwargs):
    if created:
        _safe_log('CREATE', 'CardProduct', instance.pk)
    else:
        update_fields = kwargs.get('update_fields')
        if update_fields:
            _safe_log('UPDATE', 'CardProduct', instance.pk, changes=list(update_fields))
        else:
            _safe_log('UPDATE', 'CardProduct', instance.pk)


@receiver(post_delete, sender=CardProduct)
def cardproduct_post_delete(sender, instance, **kwargs):
    _safe_log('DELETE', 'CardProduct', instance.pk)


# ============================================================
# FormPage 信号
# ============================================================

@receiver(post_save, sender=FormPage)
def formpage_post_save(sender, instance, created, **kwargs):
    if created:
        _safe_log('CREATE', 'FormPage', instance.pk)
    else:
        update_fields = kwargs.get('update_fields')
        if update_fields:
            _safe_log('UPDATE', 'FormPage', instance.pk, changes=list(update_fields))
        else:
            _safe_log('UPDATE', 'FormPage', instance.pk)


@receiver(post_delete, sender=FormPage)
def formpage_post_delete(sender, instance, **kwargs):
    _safe_log('DELETE', 'FormPage', instance.pk)


# ============================================================
# FormField 信号
# ============================================================

@receiver(post_save, sender=FormField)
def formfield_post_save(sender, instance, created, **kwargs):
    if created:
        _safe_log('CREATE', 'FormField', instance.pk)
    else:
        update_fields = kwargs.get('update_fields')
        if update_fields:
            _safe_log('UPDATE', 'FormField', instance.pk, changes=list(update_fields))
        else:
            _safe_log('UPDATE', 'FormField', instance.pk)


@receiver(post_delete, sender=FormField)
def formfield_post_delete(sender, instance, **kwargs):
    _safe_log('DELETE', 'FormField', instance.pk)


# ============================================================
# MenuItem 信号
# ============================================================

@receiver(post_save, sender=MenuItem)
def menuitem_post_save(sender, instance, created, **kwargs):
    if created:
        _safe_log('CREATE', 'MenuItem', instance.pk)
    else:
        update_fields = kwargs.get('update_fields')
        if update_fields:
            _safe_log('UPDATE', 'MenuItem', instance.pk, changes=list(update_fields))
        else:
            _safe_log('UPDATE', 'MenuItem', instance.pk)


@receiver(post_delete, sender=MenuItem)
def menuitem_post_delete(sender, instance, **kwargs):
    _safe_log('DELETE', 'MenuItem', instance.pk)
