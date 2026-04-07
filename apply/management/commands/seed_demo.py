"""演示数据种子命令：创建演示银行、卡产品与示例账号。"""  # 模块文档字符串
from django.contrib.auth.hashers import make_password  # 导入密码哈希函数
from django.core.management.base import BaseCommand  # 导入命令基类

from apply.models import Bank, CardProduct, User  # 导入需要初始化的模型

# 示例卡种与额度区间（可按需修改后重新执行 seed 或后台调整）
CARD_SPECS = [  # 元组列表：名称、类型编码、最低额度、最高额度
    ("普卡", "NORMAL", 2000, 50000),  # 普卡区间
    ("金卡", "GOLD", 10000, 100000),  # 金卡区间
    ("白金卡", "PLATINUM", 50000, 200000),  # 白金卡区间
    ("钻石卡", "DIAMOND", 100000, 500000),  # 钻石卡区间
]


class Command(BaseCommand):  # 定义管理命令类
    """执行一次写入演示环境所需的最低数据集。"""  # 类文档字符串

    help = "创建 bank 0000、四类卡产品、普通员工与审核员账号（密码均为 demo123）"  # 命令帮助文本

    def handle(self, *args, **options):  # 命令主入口
        """幂等创建或更新演示主数据记录。"""  # 方法文档字符串
        bank, _ = Bank.objects.get_or_create(  # 获取或创建演示银行
            bank_code="0000",  # 固定演示银行号
            defaults={"bank_name": "演示商业银行"},  # 新建时写入名称
        )
        for name, ptype, lo, hi in CARD_SPECS:  # 遍历卡种配置
            CardProduct.objects.update_or_create(  # 按银行+名称幂等写入
                bank=bank,  # 所属银行
                product_name=name,  # 卡种展示名
                defaults={  # 每次更新下列字段
                    "product_type": ptype,  # 内部类型编码
                    "credit_limit_min": lo,  # 最小申请金额（元）
                    "credit_limit_max": hi,  # 最大申请金额（元）
                    "annual_fee_rate": 0.0005,  # 演示年费率
                    "is_active": True,  # 启用
                },
            )
        if not User.objects.filter(bank=bank, username="staff").exists():  # 若不存在普通员工则创建
            User.objects.create(  # 创建用户记录
                username="staff",  # 登录名
                password=make_password("demo123"),  # 哈希存储演示密码
                bank=bank,  # 绑定演示银行
                role=User.ROLE_NORMAL,  # 普通员工角色
                is_staff=True,  # 允许登录后台演示（可选）
            )
        if not User.objects.filter(bank=bank, username="auditor").exists():  # 若不存在审核员则创建
            User.objects.create(  # 创建审核员
                username="auditor",  # 登录名
                password=make_password("demo123"),  # 演示密码
                bank=bank,  # 同银行
                role=User.ROLE_QUALITY,  # 审核员角色
                is_staff=True,  # 员工标记
            )
        self.stdout.write(self.style.SUCCESS("演示数据已就绪：银行 0000，卡种四类，账号 staff/auditor，密码 demo123"))  # 输出成功信息
