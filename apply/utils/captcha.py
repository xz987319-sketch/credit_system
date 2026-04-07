"""验证码工具：生成随机字符并写入会话供登录校验。"""  # 模块文档字符串说明职责
import random  # 导入随机数模块用于抽取字符
import string  # 导入预定义字符集合常量

CAPTCHA_SESSION_KEY = "login_captcha_code"  # 定义会话中存储验证码文本的键名常量


def generate_captcha_text(length: int = 6) -> str:  # 定义生成验证码函数默认长度 6
    """返回由数字与大小写字母组成的随机验证码字符串。"""  # 函数文档字符串
    alphabet = string.ascii_letters + string.digits  # 合并字母与数字作为候选字符池
    return "".join(random.choice(alphabet) for _ in range(length))  # 循环随机选取指定次数拼接成串


def store_captcha(request, code: str) -> None:  # 定义将验证码写入会话的函数
    """把验证码保存到当前会话并标记已修改以持久化。"""  # 函数文档字符串
    request.session[CAPTCHA_SESSION_KEY] = code  # 将会话键指向最新验证码文本
    request.session.modified = True  # 显式标记会话已修改确保立即保存


def captcha_matches(request, user_input: str) -> bool:  # 定义验证码比对函数
    """忽略大小写比较用户输入与会话中的验证码是否一致。"""  # 函数文档字符串
    expected = request.session.get(CAPTCHA_SESSION_KEY, "")  # 从会话读取期望验证码缺省空串
    return expected.lower() == (user_input or "").lower()  # 双方转小写后比较返回布尔结果
