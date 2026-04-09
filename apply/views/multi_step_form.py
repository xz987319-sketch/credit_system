"""
多步骤动态表单视图：基于后台配置的FormPage和FormField实现分步表单。

流程：
1. 从Session中读取已填写的表单数据
2. 根据FormPage配置获取分页结构
3. 处理每一步的表单提交，暂存到Session
4. 最后一步时，将所有数据合并保存到Application
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import uuid

from apply.models import FormPage, FormField, CardProduct, Application
from apply.utils.apply_duplicate import id_card_holds_card_product
from apply.utils.applicant_validate import (
    clean_applicant_name,
    clean_cn_mobile,
    clean_id_card_18,
)
from pypinyin import lazy_pinyin, Style


# 姓氏多音字映射表（优先使用姓氏读音）
SURNAME_POLYPHONOUS_MAP = {
    # 常见姓氏多音字
    '单': 'SHAN',    # 不是 DAN
    '解': 'XIE',     # 不是 JIE
    '区': 'OU',      # 不是 QU
    '召': 'SHAO',    # 不是 ZHAO
    '查': 'ZHA',     # 不是 CHA
    '曾': 'ZENG',    # 不是 CENG
    '乐': 'YUE',     # 不是 LE
    '仇': 'QIU',     # 不是 CHOU
    '朴': 'PIAO',    # 不是 PU
    '能': 'NAI',     # 不是 NENG
    '阚': 'KAN',     # 不是 HAN
    '卞': 'BIAN',    # 不是 BAN
    '於': 'YU',      # 不是 YU
    '哈': 'HA',      # 姓哈
    '谌': 'SHEN',    # 姓谌
    '隗': 'WEI',     # 姓隗
    '缪': 'MIAO',    # 姓缪
    '芈': 'MI',      # 姓芈
    '亓': 'QI',      # 姓亓
    '侍': 'SHI',     # 姓侍
    '仉': 'ZHANG',   # 姓仉
    '迮': 'ZE',      # 姓迮
    '俎': 'ZU',      # 姓俎
}


# ============================================================================
# 防重检测接口
# ============================================================================

@require_http_methods(["GET"])
def check_duplicate_view(request):
    """
    AJAX接口：检测身份证号是否已持有该卡种。
    用于第1步点击"下一步"前的防重拦截。
    """
    id_card = request.GET.get('id_card', '').strip().upper()
    product_id = request.GET.get('product_id', '')

    if not id_card or not product_id:
        return JsonResponse({'has_duplicate': False, 'message': ''})

    try:
        product = CardProduct.objects.get(pk=product_id, is_active=True)
    except CardProduct.DoesNotExist:
        return JsonResponse({'has_duplicate': False, 'message': '卡产品不存在'})

    if id_card_holds_card_product(id_card, product.pk, exclude_pk=None):
        return JsonResponse({
            'has_duplicate': True,
            'message': '您已拥有该卡种，不可重复申请'
        })

    return JsonResponse({'has_duplicate': False, 'message': ''})


# 中文姓名转拼音函数（使用 pypinyin 库）
def _chinese_to_pinyin(name):
    """将中文姓名转换为拼音（空格分隔，大写）。"""
    if not name:
        return ''

    # 使用 pypinyin 库转换，支持所有汉字
    raw_pinyin_list = lazy_pinyin(name, style=Style.NORMAL, strict=False)

    # 直接逐字符映射（确保索引同步）
    result = []
    for i, char in enumerate(name):
        if i < len(raw_pinyin_list):
            pinyin = raw_pinyin_list[i]
            if pinyin in '·•':
                result.append('·')
            elif char in SURNAME_POLYPHONOUS_MAP:
                # 姓氏多音字使用姓氏读音
                result.append(SURNAME_POLYPHONOUS_MAP[char])
            else:
                result.append(pinyin.upper())
        else:
            # 索引越界，保留原字符
            result.append(char)

    pinyin = ' '.join(result)

    # 清理多余的空格和·号
    while ' ·' in pinyin:
        pinyin = pinyin.replace(' ·', '·')
    while '· ' in pinyin:
        pinyin = pinyin.replace('· ', '·')
    while '  ' in pinyin:
        pinyin = pinyin.replace('  ', ' ')

    return pinyin


@csrf_exempt
def pinyin_convert_api(request):
    """
    拼音转换API - 使用pypinyin库将中文姓名转换为大写拼音
    GET参数: name - 要转换的中文姓名
    返回: {"pinyin": "ZHANG SAN"}
    """
    name = request.GET.get('name', '').strip()
    if not name:
        return JsonResponse({'pinyin': '', 'success': True})

    # lazy_pinyin 对每个字符返回一个拼音
    # · 会返回 '·' 字符串（不是空字符串）
    raw_pinyin_list = lazy_pinyin(name, style=Style.NORMAL, strict=False)

    # 直接逐字符映射（确保索引同步）
    result = []
    for i, char in enumerate(name):
        if i < len(raw_pinyin_list):
            pinyin = raw_pinyin_list[i]
            if pinyin in '·•':
                result.append('·')
            elif char in SURNAME_POLYPHONOUS_MAP:
                # 姓氏多音字使用姓氏读音
                result.append(SURNAME_POLYPHONOUS_MAP[char])
            else:
                result.append(pinyin.upper())
        else:
            # 索引越界，保留原字符
            result.append(char)

    pinyin = ' '.join(result)

    # 清理多余的空格和·号
    while ' ·' in pinyin:
        pinyin = pinyin.replace(' ·', '·')
    while '· ' in pinyin:
        pinyin = pinyin.replace('· ', '·')
    while '  ' in pinyin:
        pinyin = pinyin.replace('  ', ' ')

    return JsonResponse({'pinyin': pinyin, 'success': True})


# ============================================================================
# PC端分步表单视图
# ============================================================================

def _get_form_pages():
    """获取所有启用的表单页面及其字段，按order排序。"""
    pages = FormPage.objects.filter(is_active=True).prefetch_related('fields')
    result = []
    for page in pages:
        fields = page.fields.filter(is_active=True).order_by('sort_order')
        result.append({
            'page': page,
            'fields': list(fields),
        })
    return result


def _get_session_form_data(request):
    """从Session获取已填写的表单数据。"""
    return request.session.get('multi_step_form_data', {})


def _save_session_form_data(request, data):
    """保存表单数据到Session。"""
    request.session['multi_step_form_data'] = data


def _clear_session_form_data(request):
    """清除Session中的表单数据。"""
    if 'multi_step_form_data' in request.session:
        del request.session['multi_step_form_data']
    if 'multi_step_product_id' in request.session:
        del request.session['multi_step_product_id']
    if 'max_step_reached' in request.session:
        del request.session['max_step_reached']
    if 'form_token' in request.session:
        del request.session['form_token']
    if 'form_token_used' in request.session:
        del request.session['form_token_used']


def _validate_step_data(page_fields, post_data, product=None):
    """
    校验单页表单数据。
    返回 (is_valid, errors_dict)
    """
    errors = {}

    for field in page_fields:
        field_key = field.field_key
        field_value = post_data.get(field_key)

        # 姓名拼音字段为自动生成，不做必填校验
        if field.field_type == 'name_pinyin':
            continue

        # 图片字段：检查 base64 数据而不是文件本身
        if field.field_type == 'image':
            base64_value = post_data.get(field_key + '_base64', '')
            if isinstance(base64_value, list):
                base64_value = base64_value[0] if base64_value else ''
            if base64_value:
                base64_value = base64_value.strip()
            if field.is_required and not base64_value:
                errors[field_key] = f'{field.field_label}为必填项'
            continue

        # 其他字段 - 统一处理成字符串
        if isinstance(field_value, list):
            # 列表字段（如多选）取第一个非空值
            first_val = next((v for v in field_value if v), None)
            field_value = first_val.strip() if first_val else ''
        elif field_value is None:
            field_value = ''
        else:
            field_value = str(field_value).strip()

        # 必填校验
        if field.is_required and not field_value:
            errors[field_key] = f'{field.field_label}为必填项'
            continue

        if not field_value:
            continue

        # 用于校验的字符串值
        str_value = field_value

        # 长度校验（如果配置了max_length）
        if field.max_length and len(str_value) > field.max_length:
            errors[field_key] = f'{field.field_label}不能超过{field.max_length}个字符'
            continue

        # 根据validation_rule进行校验
        validation_rule = field.validation_rule

        # 如果没有配置validation_rule，根据field_type推断
        if not validation_rule:
            if field.field_type == 'phone':
                validation_rule = 'phone'
            elif field.field_type == 'id_card':
                validation_rule = 'id_card'
            elif field.field_type == 'name':
                validation_rule = 'name'
            elif field.field_type == 'amount':
                validation_rule = 'amount_range'

        # 应用校验规则
        if validation_rule == 'name':
            try:
                clean_applicant_name(str_value)
            except Exception as e:
                errors[field_key] = str(e)

        elif validation_rule == 'id_card':
            try:
                clean_id_card_18(str_value)
            except Exception as e:
                errors[field_key] = str(e)

        elif validation_rule == 'phone':
            try:
                clean_cn_mobile(str_value)
            except Exception as e:
                errors[field_key] = str(e)

        elif validation_rule == 'amount_range':
            try:
                from decimal import Decimal
                # 先校验数字格式
                amount_str = str_value.replace(',', '').strip()
                Decimal(amount_str)
                # 如果有产品，进行区间校验
                if product:
                    amount = Decimal(amount_str)
                    lo, hi = product.credit_limit_min, product.credit_limit_max
                    if amount < lo or amount > hi:
                        errors[field_key] = f'申请金额必须在{lo:,.2f}～{hi:,.2f}元之间'
            except Exception as e:
                errors[field_key] = '请输入有效的金额数字'

        elif field.field_type == 'number' and not validation_rule:
            try:
                # 如果是列表，取第一个元素
                val = field_value[0] if isinstance(field_value, list) else field_value
                float(val)
            except (ValueError, TypeError):
                errors[field_key] = f'{field.field_label}必须为有效数字'

        elif field.field_type == 'date':
            import datetime
            try:
                # 如果是列表，取第一个元素
                val = field_value[0] if isinstance(field_value, list) else field_value
                # 支持 YYYYMMDD 和 YYYY-MM-DD 两种格式
                if len(val) == 8:
                    datetime.datetime.strptime(val, '%Y%m%d')
                else:
                    datetime.datetime.strptime(val, '%Y-%m-%d')
            except (ValueError, TypeError):
                errors[field_key] = f'{field.field_label}日期格式不正确'

    # 申请人年龄和身份证有效期校验
    id_card_value = None
    birth_date_value = None
    id_card_expiry_value = None

    for field in page_fields:
        field_key = field.field_key
        field_value = post_data.get(field_key)
        if isinstance(field_value, list):
            field_value = field_value[0] if field_value else ''

        # 获取身份证号
        if 'id_card' in field_key.lower() or 'cert_no' in field_key.lower():
            if field_value:
                id_card_value = str(field_value).strip()

        # 获取出生日期
        if 'birth' in field_key.lower() and field.field_type == 'date':
            if field_value:
                birth_date_value = str(field_value).strip()

        # 获取身份证有效期截止日期
        if 'expiry' in field_key.lower() or 'validity' in field_key.lower():
            if field_value:
                id_card_expiry_value = str(field_value).strip().replace('-', '')

    # 年龄校验
    if id_card_value and birth_date_value:
        import re
        if re.match(r'^[1-9]\d{5}(18|19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dX]$', id_card_value, re.I):
            # 从身份证号解析出生日期
            birth_from_idcard = id_card_value[6:14]

            # 标准化出生日期为 YYYYMMDD
            birth_date_normalized = birth_date_value.replace('-', '')

            # 计算年龄
            today = datetime.date.today()
            birth_year = int(birth_from_idcard[:4])
            birth_month = int(birth_from_idcard[4:6])
            birth_day = int(birth_from_idcard[6:8])
            birth_date_obj = datetime.date(birth_year, birth_month, birth_day)

            age = today.year - birth_year
            if (today.month, today.day) < (birth_month, birth_day):
                age -= 1

            if age < 18:
                # 找到出生日期字段的 key
                for f in page_fields:
                    if 'birth' in f.field_key.lower() and f.field_type == 'date':
                        errors[f.field_key] = '未满18周岁不可申请信用卡'
                        break
            elif age > 60:
                for f in page_fields:
                    if 'birth' in f.field_key.lower() and f.field_type == 'date':
                        errors[f.field_key] = '超过60周岁不可申请信用卡'
                        break

    # 身份证有效期校验
    if id_card_expiry_value:
        today_str = today.strftime('%Y%m%d')

        # 年龄≥46时，允许有效期为"长期"（20991231）
        if id_card_expiry_value == '20991231':
            if id_card_value:
                try:
                    birth_year = int(id_card_value[6:10])
                    birth_month = int(id_card_value[10:12])
                    birth_day = int(id_card_value[12:14])
                    calc_age = today.year - birth_year
                    if (today.month, today.day) < (birth_month, birth_day):
                        calc_age -= 1
                    if calc_age < 46:
                        for f in page_fields:
                            if 'expiry' in f.field_key.lower() or 'validity' in f.field_key.lower():
                                errors[f.field_key] = '仅限46周岁及以上申请人填写"长期"作为有效期'
                                break
                except (ValueError, IndexError):
                    pass
            return (len(errors) == 0, errors)

        # 检查是否已过期
        if id_card_expiry_value < today_str:
            for f in page_fields:
                if 'expiry' in f.field_key.lower() or 'validity' in f.field_key.lower():
                    errors[f.field_key] = '身份证已过期，不可申请信用卡'
                    break

        # 检查是否即将过期（30天内）
        else:
            try:
                expiry_year = int(id_card_expiry_value[:4])
                expiry_month = int(id_card_expiry_value[4:6])
                expiry_day = int(id_card_expiry_value[6:8])
                expiry_date = datetime.date(expiry_year, expiry_month, expiry_day)
                days_until_expiry = (expiry_date - today).days
                if days_until_expiry < 30:
                    for f in page_fields:
                        if 'expiry' in f.field_key.lower() or 'validity' in f.field_key.lower():
                            errors[f.field_key] = '身份证即将过期，不可申请信用卡'
                            break
            except (ValueError, IndexError):
                pass

    return (len(errors) == 0, errors)


@require_http_methods(["GET", "POST"])
def multi_step_form_view(request, product_id):
    """
    PC端多步骤表单视图。

    GET:
    - 初始化Session，清除旧数据
    - 返回第一步表单

    POST:
    - 保存当前步骤数据到Session
    - 如果不是最后一步，返回下一步表单
    - 如果是最后一步，保存Application并跳转成功页
    """
    # 获取卡产品
    user_bank = getattr(request.user, "bank", None)
    if user_bank:
        products_qs = CardProduct.objects.filter(bank=user_bank, is_active=True)
    else:
        products_qs = CardProduct.objects.filter(is_active=True)

    product = get_object_or_404(products_qs, pk=product_id)

    # 获取所有表单页面
    form_pages = _get_form_pages()

    if not form_pages:
        messages.error(request, "暂无可用表单配置，请联系管理员")
        return redirect('apply:loan_product_list')

    # 检查是否更换了产品，如果是则清除旧的表单数据
    old_product_id = request.session.get('multi_step_product_id')
    if old_product_id and str(old_product_id) != str(product_id):
        _clear_session_form_data(request)

    # 记录产品ID到Session
    request.session['multi_step_product_id'] = product_id

    # 处理POST请求
    if request.method == "POST":
        step = int(request.POST.get('step', 0))
        is_last = request.POST.get('is_last', 'false').lower() == 'true'
        is_prev = request.POST.get('prev_step') == '1'

        current_page = form_pages[step]
        page_fields = current_page['fields']

        # 获取当前页数据
        page_data = {}
        for field in page_fields:
            # 姓名拼音字段由系统自动生成
            if field.field_type == 'name_pinyin':
                # 查找同页对应的姓名字段
                name_field = next((f for f in page_fields if f.field_type == 'name' or f.validation_rule == 'name'), None)
                if name_field:
                    name_value = request.POST.get(name_field.field_key, '').strip()
                    page_data[field.field_key] = _chinese_to_pinyin(name_value)
                else:
                    page_data[field.field_key] = ''
                continue

            # 图片字段：优先使用 base64 数据（从隐藏字段），否则使用上传的文件
            if field.field_type == 'image':
                base64_value = request.POST.get(field.field_key + '_base64', '').strip()
                if base64_value:
                    page_data[field.field_key] = base64_value
                else:
                    # 如果没有 base64，尝试获取已保存在 session 中的数据
                    session_data = _get_session_form_data(request)
                    page_data[field.field_key] = session_data.get(field.field_key, '')
                continue

            field_value = request.POST.get(field.field_key, '').strip()
            page_data[field.field_key] = field_value

        # 上一步：直接保存数据并跳转，不校验
        if is_prev:
            session_data = _get_session_form_data(request)
            session_data.update(page_data)
            _save_session_form_data(request, session_data)
            return redirect(f'{request.path}?step={step - 1}')

        # ===== Plan B Token 校验 =====（在数据校验之后、业务保存之前）
        form_token = request.session.get('form_token', '')
        submitted_token = request.POST.get('_form_token', '')
        session_token = form_token
        token_used = request.session.get('form_token_used', False)
        if not submitted_token or submitted_token != session_token or token_used:
            messages.error(request, '表单已失效，请重新发起申请')
            return render(request, 'multi_step_form.html', {
                'product': product,
                'form_pages': form_pages,
                'current_page': current_page,
                'current_step': step,
                'page_data': _get_session_form_data(request),
                'errors': {'_form_token': '表单已失效，请重新发起申请'},
                'form_token': form_token,
            })

        # 校验当前页数据（传入product用于金额区间校验）
        is_valid, errors = _validate_step_data(page_fields, request.POST, product=product)

        # 如果有校验错误，返回当前页
        if errors:
            # 合并Session中的旧数据和当前页数据
            session_data = _get_session_form_data(request)
            session_data.update(page_data)

            return render(request, 'multi_step_form.html', {
                'product': product,
                'form_pages': form_pages,
                'current_page': current_page,
                'current_step': step,
                'page_data': session_data,
                'errors': errors,
                'form_token': form_token,
            })

        # 保存当前页数据到Session
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[DEBUG] PC Step {step} - page_data keys: {list(page_data.keys())}")
        session_data = _get_session_form_data(request)
        logger.warning(f"[DEBUG] PC Step {step} - before update session_data keys: {list(session_data.keys())}")
        session_data.update(page_data)
        logger.warning(f"[DEBUG] PC Step {step} - after update session_data keys: {list(session_data.keys())}")
        _save_session_form_data(request, session_data)

        # 更新最高到达步骤（用于判断用户是否曾离开过第0页）
        current_max = request.session.get('max_step_reached', 0)
        if step > current_max:
            request.session['max_step_reached'] = step

        # 如果是最后一步，保存Application
        if is_last:
            # 标记 Token 为已用，防止刷新重提
            request.session['form_token_used'] = True
            result = _save_application(request, session_data, product, user_bank)
            # 处理防重校验返回的错误
            if isinstance(result, dict) and not result.get("success", True):
                messages.error(request, result.get("error", "申请提交失败"))
                return redirect(f'{request.path}?step={step}')
            return result
        else:
            # 返回下一步
            return redirect(f'{request.path}?step={step + 1}')

    # GET请求 - 显示指定步骤的表单
    step = int(request.GET.get('step', 0))

    # 判断是否为新的申请流程
    # 如果 max_step_reached > 0，说明用户曾经离开过第0页（如进入过第1步等），应保留数据
    # 只有首次进入或 session 中无数据时才清空
    if step == 0:
        max_step_reached = request.session.get('max_step_reached', 0)
        if max_step_reached == 0:
            # 首次进入，清除旧数据，并生成新的表单Token
            _clear_session_form_data(request)
            request.session['form_token'] = str(uuid.uuid4())
            request.session.pop('form_token_used', None)

    # 取出当前表单Token（GET step=0 时刚生成，后续步骤复用）
    form_token = request.session.get('form_token', '')

    # 限制step范围
    if step >= len(form_pages):
        step = 0

    current_page = form_pages[step]
    is_last = (step == len(form_pages) - 1)

    # 获取Session中的数据用于回填
    session_data = _get_session_form_data(request)

    # 如果是"银行专用栏"页面，自动注入银行号字段（只读）
    current_page_title = current_page['page'].page_title
    if '银行专用栏' in current_page_title:
        # 从session获取银行号，如果没有则使用当前产品的银行号
        if 'bank_code' not in session_data:
            session_data['bank_code'] = product.bank.bank_code
        else:
            # 确保使用当前产品的银行号（防止切换产品后数据不一致）
            session_data['bank_code'] = product.bank.bank_code

    return render(request, 'multi_step_form.html', {
        'product': product,
        'form_pages': form_pages,
        'current_page': current_page,
        'current_step': step,
        'page_data': session_data,
        'is_last': is_last,
        'errors': {},
        'form_token': form_token,
    })


def _save_application(request, form_data, product, user_bank):
    """保存申请记录。"""
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[DEBUG] _save_application called, form_data keys: {list(form_data.keys())}")

    # 【安全加固】强制用 product.bank.bank_code 覆盖用户提交的值，防止前端篡改
    form_data['bank_code'] = product.bank.bank_code
    logger.warning(f"[DEBUG] bank_code forced to: {product.bank.bank_code}")

    # 通过field_key直接获取值，而不是通过field_type
    applicant_name = form_data.get('applicant_name', '')
    id_card = form_data.get('id_card', '').upper()  # 统一大写，防止x/X不一致
    phone = form_data.get('phone', '')
    amount_str = form_data.get('AMOUNT', '0')  # 直接使用正确的field_key
    bank_code = form_data.get('bank_code', product.bank.bank_code)

    logger.warning(f"[DEBUG] Extracted: applicant_name={applicant_name}, id_card={id_card}, phone={phone}, amount={amount_str}, bank_code={bank_code}")

    # 处理金额
    try:
        amount_str = amount_str.replace(',', '').strip()
        from decimal import Decimal
        amount = Decimal(amount_str)
    except Exception:
        amount = Decimal('0')

    # 【申请防重校验】同一身份证对同一卡种不可重复申请
    if id_card_holds_card_product(id_card, product.pk, exclude_pk=None):
        logger.warning(f"[防重] 身份证 {id_card} 已持有卡种 {product.product_name}，拒绝新建申请")
        return {"success": False, "error": "您已拥有该卡种，不可重复申请"}

    # 创建申请记录
    app = Application.objects.create(
        user=request.user,
        bank=product.bank,
        card_product=product,
        applicant_name=applicant_name,
        id_card=id_card,
        phone=phone,
        amount=amount,
        status=Application.ST_PENDING_FIRST,
        form_data=form_data,  # 存储完整的动态表单数据
    )

    # 清除Session数据
    _clear_session_form_data(request)

    messages.success(request, "贷款申请提交成功，您的申请已进入初审队列。")
    return redirect('apply:apply_success', pk=app.pk)


# ============================================================================
# H5端多步骤表单视图
# ============================================================================

@require_http_methods(["GET", "POST"])
def h5_multi_step_form_view(request, product_id):
    """
    H5端多步骤表单视图（移动端适配）。

    逻辑同PC端，但使用H5模板。
    """
    # 获取卡产品
    products_qs = CardProduct.objects.filter(is_active=True)
    product = get_object_or_404(products_qs, pk=product_id)

    # 获取所有表单页面
    form_pages = _get_form_pages()

    if not form_pages:
        return JsonResponse({'error': '暂无可用表单配置'}, status=400)

    # 检查是否更换了产品，如果是则清除旧的表单数据
    old_product_id = request.session.get('multi_step_product_id')
    if old_product_id and str(old_product_id) != str(product_id):
        _clear_session_form_data(request)

    # 记录产品ID到Session
    request.session['multi_step_product_id'] = product_id

    # 处理POST请求
    if request.method == "POST":
        step = int(request.POST.get('step', 0))
        is_last = request.POST.get('is_last', 'false').lower() == 'true'
        is_prev = request.POST.get('prev_step') == '1'

        current_page = form_pages[step]
        page_fields = current_page['fields']

        # 获取当前页数据
        page_data = {}
        for field in page_fields:
            # 姓名拼音字段由系统自动生成
            if field.field_type == 'name_pinyin':
                # 查找同页对应的姓名字段
                name_field = next((f for f in page_fields if f.field_type == 'name' or f.validation_rule == 'name'), None)
                if name_field:
                    name_value = request.POST.get(name_field.field_key, '').strip()
                    page_data[field.field_key] = _chinese_to_pinyin(name_value)
                else:
                    page_data[field.field_key] = ''
                continue

            # 图片字段：优先使用 base64 数据（从隐藏字段），否则使用上传的文件
            if field.field_type == 'image':
                base64_value = request.POST.get(field.field_key + '_base64', '').strip()
                if base64_value:
                    page_data[field.field_key] = base64_value
                else:
                    # 如果没有 base64，尝试获取已保存在 session 中的数据
                    session_data = _get_session_form_data(request)
                    page_data[field.field_key] = session_data.get(field.field_key, '')
                continue

            field_value = request.POST.get(field.field_key, '').strip()
            page_data[field.field_key] = field_value

        # 上一步：直接保存数据并跳转，不校验
        if is_prev:
            session_data = _get_session_form_data(request)
            session_data.update(page_data)
            _save_session_form_data(request, session_data)
            return redirect(f'{request.path}?step={step - 1}')

        # ===== Plan B Token 校验 =====
        form_token = request.session.get('form_token', '')
        submitted_token = request.POST.get('_form_token', '')
        session_token = form_token
        token_used = request.session.get('form_token_used', False)
        if not submitted_token or submitted_token != session_token or token_used:
            messages.error(request, '表单已失效，请重新发起申请')
            return render(request, 'h5_multi_step_form.html', {
                'product': product,
                'form_pages': form_pages,
                'current_page': current_page,
                'current_step': step,
                'page_data': _get_session_form_data(request),
                'errors': {'_form_token': '表单已失效，请重新发起申请'},
                'form_token': form_token,
            })

        # 校验当前页数据（传入product用于金额区间校验）
        # 合并 page_data 到 POST，确保图片的 base64 数据被正确验证
        validate_data = dict(request.POST)
        for key, value in page_data.items():
            if value:  # 只更新有值的字段
                validate_data[key + '_base64'] = [value]
        is_valid, errors = _validate_step_data(page_fields, validate_data, product=product)

        if errors:
            session_data = _get_session_form_data(request)
            session_data.update(page_data)

            return render(request, 'h5_multi_step_form.html', {
                'product': product,
                'form_pages': form_pages,
                'current_page': current_page,
                'current_step': step,
                'page_data': session_data,
                'errors': errors,
                'is_last': is_last,
                'form_token': form_token,
            })

        # 保存当前页数据到Session
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[DEBUG] H5 Step {step} - page_data keys: {list(page_data.keys())}")
        session_data = _get_session_form_data(request)
        logger.warning(f"[DEBUG] H5 Step {step} - before update session_data keys: {list(session_data.keys())}")
        session_data.update(page_data)
        logger.warning(f"[DEBUG] H5 Step {step} - after update session_data keys: {list(session_data.keys())}")
        _save_session_form_data(request, session_data)

        # 更新最高到达步骤（用于判断用户是否曾离开过第0页）
        current_max = request.session.get('max_step_reached', 0)
        if step > current_max:
            request.session['max_step_reached'] = step

        if is_last:
            # 标记 Token 为已用，防止刷新重提
            request.session['form_token_used'] = True
            result = _h5_save_application(request, session_data, product)
            # 处理防重校验返回的错误
            if isinstance(result, dict) and not result.get("success", True):
                messages.error(request, result.get("error", "申请提交失败"))
                return redirect(f'{request.path}?step={step}')
            return result
        else:
            return redirect(f'{request.path}?step={step + 1}')

    # GET请求
    step = int(request.GET.get('step', 0))

    # 判断是否为新的申请流程
    # 如果 max_step_reached > 0，说明用户曾经离开过第0页，应保留数据
    if step == 0:
        max_step_reached = request.session.get('max_step_reached', 0)
        if max_step_reached == 0:
            _clear_session_form_data(request)
            request.session['form_token'] = str(uuid.uuid4())
            request.session.pop('form_token_used', None)

    if step >= len(form_pages):
        step = 0

    current_page = form_pages[step]
    is_last = (step == len(form_pages) - 1)
    session_data = _get_session_form_data(request)
    form_token = request.session.get('form_token', '')

    # 如果是"银行专用栏"页面，自动注入银行号字段（只读）
    current_page_title = current_page['page'].page_title
    if '银行专用栏' in current_page_title:
        # 从session获取银行号，如果没有则使用当前产品的银行号
        if 'bank_code' not in session_data:
            session_data['bank_code'] = product.bank.bank_code
        else:
            # 确保使用当前产品的银行号（防止切换产品后数据不一致）
            session_data['bank_code'] = product.bank.bank_code

    return render(request, 'h5_multi_step_form.html', {
        'product': product,
        'form_pages': form_pages,
        'current_page': current_page,
        'current_step': step,
        'page_data': session_data,
        'is_last': is_last,
        'errors': {},
        'form_token': form_token,
    })


def _h5_save_application(request, form_data, product):
    """H5端保存申请记录。"""
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[DEBUG] _h5_save_application called, form_data keys: {list(form_data.keys())}")

    # 【安全加固】强制用 product.bank.bank_code 覆盖用户提交的值，防止前端篡改
    form_data['bank_code'] = product.bank.bank_code
    logger.warning(f"[DEBUG] bank_code forced to: {product.bank.bank_code}")

    # 直接使用正确的field_key获取值
    applicant_name = form_data.get('applicant_name', '')
    id_card = form_data.get('id_card', '').upper()  # 统一大写，防止x/X不一致
    phone = form_data.get('phone', '')
    amount_str = form_data.get('AMOUNT', '0')  # 直接使用正确的field_key
    bank_code = form_data.get('bank_code', product.bank.bank_code)

    logger.warning(f"[DEBUG] Extracted: applicant_name={applicant_name}, id_card={id_card}, phone={phone}, amount={amount_str}, bank_code={bank_code}")

    try:
        amount_str = amount_str.replace(',', '').strip()
        from decimal import Decimal
        amount = Decimal(amount_str)
    except Exception:
        amount = Decimal('0')

    # 【申请防重校验】同一身份证对同一卡种不可重复申请
    if id_card_holds_card_product(id_card, product.pk, exclude_pk=None):
        logger.warning(f"[防重] H5端身份证 {id_card} 已持有卡种 {product.product_name}，拒绝新建申请")
        return {"success": False, "error": "您已拥有该卡种，不可重复申请"}

    app = Application.objects.create(
        user=request.user if request.user.is_authenticated else None,
        bank=product.bank,
        card_product=product,
        applicant_name=applicant_name,
        id_card=id_card,
        phone=phone,
        amount=amount,
        status=Application.ST_PENDING_FIRST,
        form_data=form_data,
    )

    _clear_session_form_data(request)

    # H5专用成功页（移动端适配，有5秒倒计时和返回银行大厅按钮）
    # server_host 用于手机访问时拼接正确的局域网地址
    return render(request, 'apply_h5_success.html', {
        'application': app,
        'server_host': request.get_host(),
    })
