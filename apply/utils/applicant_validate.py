"""进件字段校验：姓名、18 位身份证与中国大陆手机号。"""  # 模块文档字符串
import re  # 导入正则模块

from django.core.exceptions import ValidationError  # 导入 Django 验证异常供表单复用

# 申请人姓名：1～15 个字符
# 核心约束：
#   1. 只能包含汉字和间隔符「·」
#   2. 首尾必须是汉字（不能是·）
#   3. ·后面必须紧跟至少2个汉字（形成完整段）
#   4. 总长度1-15字符

# 18 位身份证：地区+出生日期+顺序码+校验位，末位可为数字或大写 X（小写 x 会先转大写再匹配）
ID_CARD_18_PATTERN = re.compile(
    r"^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dX]$"
)

# 中国大陆手机号：1 开头 11 位，第二位为常见号段
CN_MOBILE_PATTERN = re.compile(
    r"^1(3[0-9]|4[5-9]|5[0-35-9]|6[2567]|7[0-8]|8[0-9]|9[0-35-9])\d{8}$"
)


def clean_applicant_name(value: str) -> str:
    """去除首尾空白并校验姓名规则，通过则返回原串。
    
    规则：
    1. 只能包含汉字和「·」
    2. 首位和末位必须是汉字（不能是·）
    3. 「·」后面必须紧跟至少2个汉字（构成一个段）
    4. 总长度1-15字符
    """
    text = (value or "").strip()
    
    if len(text) < 1 or len(text) > 15:
        raise ValidationError("姓名须为 1～15 个汉字")
    
    # 检查首位和末位
    if text[0] == '·' or text[-1] == '·':
        raise ValidationError("姓名格式不正确。「·」间隔符只能放在名字中间，不能在首位或末尾")
    
    # 检查每个字符
    i = 0
    while i < len(text):
        char = text[i]
        
        if char == '·':
            # · 后面必须紧跟至少2个汉字
            if i == len(text) - 1:  # ·在末尾
                raise ValidationError("姓名格式不正确。「·」间隔符只能放在名字中间，不能在首位或末尾")
            # 检查·后面连续的汉字数量
            j = i + 1
            hanzi_count = 0
            while j < len(text) and '\u4e00' <= text[j] <= '\u9fff':
                hanzi_count += 1
                j += 1
            if hanzi_count < 2:
                raise ValidationError("姓名格式不正确。「·」间隔符后须紧跟至少2个汉字")
            # 跳过·和连续的汉字
            i = j
        elif '\u4e00' <= char <= '\u9fff':
            i += 1
        else:
            raise ValidationError("姓名格式不正确。只能包含汉字和少数民族间隔符「·」")
    
    return text


def clean_id_card_18(value: str) -> str:
    """校验 18 位身份证格式，将小写 x 规范为大写 X 后返回。"""
    raw = (value or "").strip()  # 去空白
    upper = raw.upper() if raw else raw  # 末位小写 x 转大写 X
    if not ID_CARD_18_PATTERN.fullmatch(upper):  # 按业务正则校验
        raise ValidationError("身份证号码格式不正确，请核对 18 位号码与出生日期")
    return upper  # 返回规范后的证件号


def clean_cn_mobile(value: str) -> str:
    """校验中国大陆手机号号段与长度。"""
    digits = (value or "").strip()  # 去空白
    if not CN_MOBILE_PATTERN.fullmatch(digits):  # 匹配号段规则
        raise ValidationError("请输入有效的 11 位中国大陆手机号码")
    return digits  # 返回手机号
