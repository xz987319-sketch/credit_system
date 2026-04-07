"""工具包导出：对外暴露常用辅助函数。"""  # 包文档字符串
from apply.utils.applicant_validate import (  # 导出进件字段校验函数
    clean_applicant_name,  # 姓名规则
    clean_cn_mobile,  # 手机号规则
    clean_id_card_18,  # 身份证规则
)
from apply.utils.apply_duplicate import id_card_holds_card_product  # 导出防重查询函数
from apply.utils.bank_scope import scope_by_bank  # 导出银行范围过滤函数
from apply.utils.captcha import (  # 导出验证码相关函数与常量
    CAPTCHA_SESSION_KEY,  # 会话键常量
    captcha_matches,  # 比对函数
    generate_captcha_text,  # 生成函数
    store_captcha,  # 存储函数
)

__all__ = [  # 定义公开符号列表
    "clean_applicant_name",  # 姓名校验
    "clean_cn_mobile",  # 手机校验
    "clean_id_card_18",  # 身份证校验
    "id_card_holds_card_product",  # 证件+卡种防重
    "CAPTCHA_SESSION_KEY",  # 包含会话键
    "captcha_matches",  # 包含比对函数
    "generate_captcha_text",  # 包含生成函数
    "store_captcha",  # 包含存储函数
    "scope_by_bank",  # 包含范围过滤函数
]
