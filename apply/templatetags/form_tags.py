"""自定义模板标签"""

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """从字典获取值，类似 dict|get_item:key"""
    if dictionary is None:
        return ''
    return dictionary.get(key, '')


@register.filter
def index(list_obj, index):
    """获取列表指定索引的元素，类似 list|index:0"""
    try:
        return list_obj[index]
    except (IndexError, TypeError):
        return None


@register.filter
def parse_options(options_string):
    """
    解析选项字符串为列表。
    格式：value1|label1\nvalue2|label2
    或：value1,label1\nvalue2,label2
    """
    if not options_string:
        return []

    options = []
    lines = options_string.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 支持 | 或 , 分隔
        if '|' in line:
            parts = line.split('|', 1)
        elif ',' in line:
            parts = line.split(',', 1)
        else:
            parts = [line, line]

        options.append({
            'value': parts[0].strip(),
            'label': parts[1].strip() if len(parts) > 1 else parts[0].strip(),
        })

    return options


# 核心字段集合（已在主表单中展示，此处不重复显示）
CORE_FIELD_KEYS = {
    'applicant_name',  # 申请人姓名
    'id_card',         # 身份证号
    'phone',           # 手机号
    'amount',          # 申请金额
    'card_product',    # 卡种
    'supplementary_note',  # 补充说明
    'return_reason',   # 退回原因
}

# 核心字段默认标签
CORE_FIELD_DEFAULT_LABELS = {
    'applicant_name': '申请人姓名',
    'id_card': '证件号码',
    'phone': '手机号',
    'amount': '申请金额（元）',
    'card_product': '申请卡种',
    'supplementary_note': '补充说明',
    'return_reason': '退回原因',
}


@register.simple_tag
def get_core_field_keys():
    """返回核心字段键集合"""
    return CORE_FIELD_KEYS


@register.simple_tag
def get_core_field_labels():
    """
    返回核心字段标签字典。
    如果 FormField 中有配置，使用配置的标签；否则使用默认标签。
    注意：匹配时忽略大小写（如 amount 和 AMOUNT 都匹配 'amount'）。
    """
    try:
        from apply.models.form_config import FormField

        # 从数据库获取配置的标签（key 统一转为小写存储）
        configured_labels = {}
        for field in FormField.objects.filter(is_active=True):
            key_lower = field.field_key.lower()
            if key_lower in CORE_FIELD_DEFAULT_LABELS:
                configured_labels[key_lower] = field.field_label

        # 合并：使用配置的标签，没有则使用默认标签
        result = {}
        for key, default_label in CORE_FIELD_DEFAULT_LABELS.items():
            result[key] = configured_labels.get(key, default_label)

        return result
    except Exception:
        # 如果出错，返回默认标签
        return CORE_FIELD_DEFAULT_LABELS.copy()


@register.filter
def get_option_label(options_string, value):
    """
    根据选项值获取对应的显示标签。
    格式：value1|label1\\nvalue2|label2
    """
    if not options_string or not value:
        return ''

    lines = options_string.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '|' in line:
            parts = line.split('|', 1)
        elif ',' in line:
            parts = line.split(',', 1)
        else:
            parts = [line, line]

        if parts[0].strip() == value:
            return parts[1].strip() if len(parts) > 1 else parts[0].strip()

    return ''


@register.filter
def get_checkbox_labels(options_string, values):
    """
    根据复选框值列表获取对应的显示标签。
    values 可以是逗号分隔的字符串或列表。
    """
    if not options_string:
        return ''

    # 解析 values
    if isinstance(values, str):
        value_list = [v.strip() for v in values.split(',') if v.strip()]
    elif isinstance(values, (list, tuple)):
        value_list = [str(v).strip() for v in values if v]
    else:
        value_list = []

    if not value_list:
        return ''

    lines = options_string.strip().split('\n')
    labels = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if '|' in line:
            parts = line.split('|', 1)
        elif ',' in line:
            parts = line.split(',', 1)
        else:
            parts = [line, line]

        if parts[0].strip() in value_list:
            labels.append(parts[1].strip() if len(parts) > 1 else parts[0].strip())

    return '、'.join(labels) if labels else ''


@register.filter
def has_checkbox_value(values, target_value):
    """
    检查复选框值列表中是否包含目标值。
    values 可以是逗号分隔的字符串或列表。
    """
    if not values or not target_value:
        return False

    # 解析 values
    if isinstance(values, str):
        value_list = [v.strip() for v in values.split(',') if v.strip()]
    elif isinstance(values, (list, tuple)):
        value_list = [str(v).strip() for v in values if v]
    else:
        value_list = []

    return target_value in value_list


@register.filter
def first_page(pages):
    """
    返回第一页（基本信息页），用于只读展示。
    """
    if not pages:
        return None
    # 支持 QuerySet 和列表
    try:
        return pages[0]
    except (IndexError, TypeError):
        return None


@register.filter
def exclude_first_page(pages):
    """
    返回除第一页之外的所有页面，用于可编辑展示。
    """
    if not pages:
        return []
    # 支持 QuerySet 和列表
    try:
        return list(pages)[1:]
    except (IndexError, TypeError, AttributeError):
        return []


@register.filter
def filter_first_page(pages):
    """
    返回只包含第一页的列表，用于只读模式渲染。
    """
    if not pages:
        return []
    try:
        return [pages[0]]
    except (IndexError, TypeError):
        return []


@register.filter
def is_same_page(page1, page2):
    """
    比较两个页面是否是同一页面。
    """
    if not page1 or not page2:
        return False
    return page1.pk == page2.pk


@register.filter
def or_readonly(val1, val2):
    """
    返回两个值的或结果，用于判断是否只读。
    """
    return val1 or val2
