"""自定义认证后端：支持银行号加用户名密码组合登录。"""  # 模块文档字符串
from typing import Optional  # 导入可选类型注解工具

from django.contrib.auth.backends import BaseBackend  # 导入认证后端抽象基类
from django.contrib.auth.hashers import check_password  # 导入密码哈希校验函数

from apply.models import User  # 导入自定义用户模型


class BankBackend(BaseBackend):  # 定义银行组合认证后端类
    """使用银行编码、用户名与密码定位用户并校验凭证。"""  # 类文档字符串

    def authenticate(self, request, bank_code=None, username=None, password=None, **kwargs):  # 实现认证接口
        """根据银行号与用户名查找用户并验证密码哈希。"""  # 方法文档字符串
        if not bank_code or not username or password is None:  # 若缺少任一必要参数则无法认证
            return None  # 返回 None 表示本后端无法处理
        user = User.objects.filter(bank__bank_code=bank_code, username=username).first()  # 按联合条件查询首个用户
        if user is None:  # 若未找到匹配用户
            return None  # 返回 None 让其他后端继续尝试
        if check_password(password, user.password):  # 使用 Django 哈希校验密码是否匹配
            return user  # 校验成功返回用户实例
        return None  # 密码错误返回 None

    def get_user(self, user_id: int) -> Optional[User]:  # 实现根据主键加载用户
        """会话恢复时根据用户主键重新获取用户对象。"""  # 方法文档字符串
        try:  # 尝试查询用户避免异常中断
            return User.objects.get(pk=user_id)  # 按主键精确获取用户
        except User.DoesNotExist:  # 捕获用户不存在异常
            return None  # 返回 None 表示会话失效
