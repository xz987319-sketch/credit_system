"""普通员工视图：本行申请列表、退回补充编辑与详情比对。"""  # 模块文档字符串
from decimal import Decimal  # 导入高精度小数类型用于额度比较

from django.contrib import messages  # 导入消息框架
from django.contrib.auth.decorators import login_required  # 导入登录要求装饰器
from django.core.paginator import Paginator  # 导入分页器类
from django.db.models import Prefetch, Q  # 导入 Q 对象组合查询条件
from django.shortcuts import get_object_or_404, redirect, render  # 导入快捷函数
from django.views.decorators.http import require_http_methods  # 导入 HTTP 方法限制

from apply.forms import EmployeeApplyForm, ReturnEditForm  # 导入员工申请表单和退回编辑表单
from apply.models import Application, CardProduct  # 导入模型
from apply.utils.bank_scope import scope_by_bank  # 导入银行范围过滤工具
from apply.views.access import can_access_application  # 导入单条申请访问判断


@login_required  # 列表需登录
@require_http_methods(["GET"])  # 列表仅 GET
def my_applications_view(request):  # 定义我的申请列表视图
    """分页展示本行申请并支持姓名身份证搜索与状态筛选。"""  # 视图文档字符串
    qs = Application.objects.select_related("bank", "card_product")  # 预取关联减少查询次数
    qs = scope_by_bank(qs, request.user)  # 按用户银行范围过滤查询集
    keyword = (request.GET.get("q") or "").strip()  # 读取搜索关键字并去空白
    if keyword:  # 若关键字非空则构造模糊查询
        qs = qs.filter(Q(applicant_name__icontains=keyword) | Q(id_card__icontains=keyword))  # 姓名或身份证匹配
    status = (request.GET.get("status") or "").strip()  # 读取状态筛选参数
    if status:  # 若传入状态则过滤
        qs = qs.filter(status=status)  # 按状态精确筛选
    paginator = Paginator(qs.order_by("-created_at"), 10)  # 每页 10 条按创建时间倒序分页
    page_obj = paginator.get_page(request.GET.get("page"))  # 获取当前页对象
    return render(  # 渲染列表模板
        request,  # 传入请求对象
        "my_applications.html",  # 指定模板路径
        {"page_obj": page_obj, "keyword": keyword, "status": status},  # 传递分页与筛选条件
    )


# =============================================================================
# 员工信用卡申请视图
# =============================================================================
# 业务说明：
#   已登录员工可在自己的银行范围内创建信用卡申请单。
#   与 H5 匿名申请的区别：
#     - H5：匿名用户只能选演示银行（0000），不绑定员工
#     - 前台：登录员工只能选自己银行的产品，申请关联到当前员工
#
# 安全设计（三层防护）：
#   第1层：视图层 — 从 request.user.bank 取银行，若无银行则拒绝访问
#   第2层：表单层 — card_product queryset 仅包含当前用户银行的产品
#   第3层：表单层 — clean() 再次校验卡种是否属于当前用户银行（防 POST 伪造）
# =============================================================================

# =============================================================================
# 贷款申请视图（前台登录用户）
# =============================================================================
# 业务说明：
#   已登录员工可在自己的银行范围内创建贷款申请单。
#   超级管理员可申请所有银行的卡产品，普通员工只能申请自己银行的卡产品。
#
# 与 H5 匿名申请的区别：
#   - H5：匿名用户只能选演示银行（0000），不绑定员工
#   - 前台：登录员工可以申请自己银行的卡产品，申请关联到当前员工
#
# 安全设计（与员工信用卡申请一致）：
#   第1层：视图层 — 获取用户银行，超级管理员 bank=None 时可看全部产品
#   第2层：表单层 — card_product queryset 过滤（超管不过滤，普通员工仅本行）
#   第3层：表单层 — clean() 再次校验卡种是否属于当前用户银行
# =============================================================================

@login_required  # 必须已登录
@require_http_methods(["GET", "POST"])  # GET 展示表单，POST 提交申请
def loan_apply_view(request):
    """
    处理登录用户提交贷款申请的核心视图（前台页面）。

    逻辑说明：
    - 超级管理员（bank=None）：可申请所有银行的启用卡产品
    - 普通员工（bank有值）：只能申请自己银行的启用卡产品

    GET 请求  →  展示空白表单（卡种下拉根据用户角色过滤）
    POST 请求 →  校验并保存申请记录，跳转成功页
    """
    from apply.forms import H5ApplyForm  # 复用 H5 表单的校验逻辑

    # -------------------------------------------------------------------------
    # 获取当前用户银行信息
    # -------------------------------------------------------------------------
    user_bank = getattr(request.user, "bank", None)  # 安全获取

    # -------------------------------------------------------------------------
    # 根据用户银行过滤卡产品
    # -------------------------------------------------------------------------
    if user_bank is None:
        # 超级管理员：可申请所有银行的启用卡产品
        card_products = CardProduct.objects.filter(is_active=True)
    else:
        # 普通员工：只能申请自己银行的启用卡产品
        card_products = CardProduct.objects.filter(bank=user_bank, is_active=True)

    products = list(card_products)  # 立即执行查询，避免模板中多次访问数据库

    # -------------------------------------------------------------------------
    # 处理表单提交（POST 请求）
    # -------------------------------------------------------------------------
    if request.method == "POST":
        form = H5ApplyForm(request.POST, card_queryset=card_products)

        if form.is_valid():
            app = form.save(commit=False)

            # 根据用户银行设置申请关联
            if user_bank is not None:
                app.bank = user_bank  # 普通员工：强制关联本行
            else:
                # 超级管理员：从所选卡产品获取银行信息
                app.bank = app.card_product.bank

            app.user = request.user  # 关联提交员工
            app.status = Application.ST_PENDING_FIRST  # 初始状态：待初审

            app.save()

            messages.success(request, "贷款申请提交成功，您的申请已进入初审队列。")
            return redirect("apply:apply_success", pk=app.pk)
        else:
            messages.error(request, "请根据提示修正表单中的错误。")
    else:
        form = H5ApplyForm(card_queryset=card_products)

    return render(
        request,
        "loan_apply.html",
        {
            "form": form,
            "products": products,
            "user_bank": user_bank,
            "is_superuser": request.user.is_superuser,
        },
    )


# =============================================================================
# PC端贷款申请三步流程视图
# =============================================================================
def _get_loan_products(request):
    """
    根据当前用户获取可申请的卡产品列表。
    - 超级管理员：所有银行
    - 普通员工：本行产品
    """
    user_bank = getattr(request.user, "bank", None)
    if user_bank is None:
        return CardProduct.objects.filter(is_active=True), user_bank
    else:
        return CardProduct.objects.filter(bank=user_bank, is_active=True), user_bank


@login_required
@require_http_methods(["GET"])
def loan_product_list_view(request):
    """PC端卡种列表页：展示所有可申请的信用卡产品。"""
    products, user_bank = _get_loan_products(request)
    products = list(products.select_related("bank"))
    bank = user_bank if user_bank else products[0].bank if products else None
    return render(request, "loan_product_list.html", {
        "products": products,
        "bank": bank,
        "user_bank": user_bank,
        "is_superuser": request.user.is_superuser,
    })


@login_required
@require_http_methods(["GET"])
def loan_product_detail_view(request, pk: int):
    """PC端卡种详情页：展示产品特点、要点、资料、注意事项。"""
    products, user_bank = _get_loan_products(request)
    product = get_object_or_404(products, pk=pk)
    return render(request, "loan_product_detail.html", {
        "product": product,
        "user_bank": user_bank,
        "is_superuser": request.user.is_superuser,
    })


@login_required
@require_http_methods(["GET", "POST"])
def loan_apply_with_product_view(request, product_id=None):
    """PC端申请表单：预选指定卡种，支持提交申请。"""
    from apply.forms import H5ApplyForm

    products_qs, user_bank = _get_loan_products(request)
    products = list(products_qs)
    selected_product = None

    if product_id:
        selected_product = products_qs.filter(pk=product_id).first()

    if request.method == "GET":
        form = H5ApplyForm(card_queryset=products_qs)
        if selected_product:
            form.fields["card_product"].initial = selected_product
        return render(request, "loan_apply_form.html", {
            "form": form,
            "products": products,
            "selected_product": selected_product,
            "user_bank": user_bank,
            "is_superuser": request.user.is_superuser,
        })

    # POST
    form = H5ApplyForm(request.POST, card_queryset=products_qs)
    if product_id and selected_product:
        form.fields["card_product"].initial = selected_product

    if form.is_valid():
        app = form.save(commit=False)
        if user_bank is not None:
            app.bank = user_bank
        else:
            app.bank = app.card_product.bank
        app.user = request.user
        app.status = Application.ST_PENDING_FIRST
        app.save()
        messages.success(request, "贷款申请提交成功，您的申请已进入初审队列。")
        return redirect("apply:apply_success", pk=app.pk)
    else:
        messages.error(request, "请根据提示修正表单中的错误。")
        return render(request, "loan_apply_form.html", {
            "form": form,
            "products": products,
            "selected_product": selected_product,
            "user_bank": user_bank,
            "is_superuser": request.user.is_superuser,
        })


@login_required  # 必须已登录，未登录跳转到登录页
@require_http_methods(["GET", "POST"])  # GET 展示表单，POST 提交申请
def employee_apply_view(request):  # 定义员工申请视图函数
    """
    处理员工登录后提交信用卡申请的核心视图。

    流程说明：
    GET 请求  →  展示空白表单（卡种下拉仅含本行产品）
    POST 请求 →  校验并保存申请记录，跳转成功页

    为什么用 login_required？
    只有已登录用户才有 request.user.bank，未登录用户无法确定所属银行。
    """
    # -------------------------------------------------------------------------
    # 第1层防护：从当前登录用户获取银行信息
    # -------------------------------------------------------------------------
    # request.user 是 Django 认证系统注入的 User 实例
    # bank 是 User 模型的外键字段（可为空，仅超级管理员可能为空）
    user_bank = getattr(request.user, "bank", None)  # 安全获取，属性不存在返回 None

    # 若用户未绑定银行（理论上只有超管），不允许提交申请
    if user_bank is None:
        messages.error(request, "您的账号未绑定银行，无法提交申请，请联系管理员。")
        return redirect("apply:home")  # 重定向回首页，避免白屏

    # -------------------------------------------------------------------------
    # 获取当前用户银行的启用卡产品列表
    # -------------------------------------------------------------------------
    # 过滤条件说明：
    #   - bank=user_bank：只选当前用户所属银行发行的产品
    #   - is_active=True：只选启用状态的产品（下架产品不可申请）
    # -------------------------------------------------------------------------
    card_products = CardProduct.objects.filter(
        bank=user_bank,  # 当前用户的银行
        is_active=True,  # 仅启用中的卡产品
    )

    # 若该银行没有任何启用卡产品，展示友好提示而非空下拉框
    # 注意：模板中会根据 products|length 判断是否显示提示
    products = list(card_products)  # 立即执行查询，避免模板中多次访问数据库

    # -------------------------------------------------------------------------
    # 处理表单提交（POST 请求）
    # -------------------------------------------------------------------------
    if request.method == "POST":
        # 关键参数说明：
        #   - request.POST：包含用户提交的字段数据，Django 用它校验必填和格式
        #   - user_bank=user_bank：将当前用户银行传给表单，用于 bank 字段只读展示
        #   - card_queryset=card_products：过滤后的卡产品查询集，仅含本行产品
        #   - initial={"bank": user_bank}：表单初始值，确保 bank 字段默认选中本行
        form = EmployeeApplyForm(
            request.POST,  # 绑定用户提交的 POST 数据
            user_bank=user_bank,  # 注入当前用户银行（用于生成只读 bank 字段）
            card_queryset=card_products,  # 注入受限的卡产品查询集
        )

        if form.is_valid():  # 执行所有字段的 clean_xxx 和表单级 clean()
            # form.clean() 已校验：
            #   1. 卡种 belong_to 当前用户银行（防前端绕过）
            #   2. 身份证+卡种 不重复申请（业务防重）
            # 此时 cleaned_data 包含所有已校验的数据

            # save(commit=False) 生成 Application 实例，但暂不写入数据库
            # 这样我们可以再填充几个服务端必填字段
            app = form.save(commit=False)

            # 填充服务端字段（前端无法伪造）
            app.bank = user_bank  # 强制关联当前用户银行（最关键！）
            app.user = request.user  # 关联提交员工（便于追溯）
            app.status = Application.ST_PENDING_FIRST  # 初始状态：待初审

            app.save()  # 写入数据库，自动生成主键和 created_at

            # 保存成功后，跳转到成功页并传递申请主键
            messages.success(request, "申请提交成功，您的申请已进入初审队列。")
            return redirect("apply:apply_success", pk=app.pk)  # 申请编号展示页
        else:
            # 表单校验失败（字段格式错误 或 clean() 中业务校验失败）
            # 返回带错误的表单，模板中用 {{ form.errors }} 或 {{ form.non_field_errors }} 展示
            messages.error(request, "请根据提示修正表单中的错误。")
    else:
        # -------------------------------------------------------------------------
        # 处理表单展示（GET 请求）
        # -------------------------------------------------------------------------
        # initial={"bank": user_bank} 确保 bank 字段预填充当前用户银行
        # card_queryset=card_products 确保下拉仅展示本行产品
        form = EmployeeApplyForm(
            user_bank=user_bank,  # 注入当前用户银行
            card_queryset=card_products,  # 注入受限卡产品查询集
        )

    # -------------------------------------------------------------------------
    # 渲染模板：传递表单实例和产品列表
    # -------------------------------------------------------------------------
    return render(
        request,  # 请求对象（Django 会自动传递 TemplateResponseMiddleware 等中间件数据）
        "employee_apply.html",  # 员工申请页面模板（需新建）
        {
            "form": form,  # 表单实例，含所有字段和错误信息
            "products": products,  # 产品列表，用于判断是否为空（无产品时显示提示）
            "user_bank": user_bank,  # 当前用户银行，用于模板中展示银行名称
        },
    )


def _validate_page_for_return_edit(page_fields, post_data, existing_form_data, product=None):
    """
    退回编辑模式下的页面校验。
    - 跳过图片字段的必填校验（已有图片保留）
    - 跳过银行专用栏的必填校验
    - 对其他字段进行正常校验
    返回错误字典。
    """
    errors = {}
    
    for field in page_fields:
        field_key = field.field_key
        
        # 跳过姓名拼音（自动生成）
        if field.field_type == 'name_pinyin':
            continue
        
        # 图片字段：检查 base64 数据或已有图片
        if field.field_type == 'image':
            # 检查是否有新的 base64 数据或已有图片
            base64_value = post_data.get(field_key + '_base64', '')
            if isinstance(base64_value, list):
                base64_value = base64_value[0] if base64_value else ''
            
            # 检查是否已有图片（退回编辑模式下保留）
            existing_value = existing_form_data.get(field_key)
            has_value = bool(base64_value and base64_value.strip()) or bool(existing_value and existing_value.strip())
            
            # 退回编辑模式下不强制要求必填（因为保留原图片）
            if field.is_required and not has_value:
                errors[field_key] = f'{field.field_label}为必填项'
            continue
        
        # 只对真正只读的 bank_code 字段跳过必填校验（由系统自动填充，用户无法编辑）
        # 其他银行专用栏字段（如 BA_POST、BNK_REF_NAME 等）如果 is_readonly=False，用户可以编辑，仍需校验必填
        if field_key == 'bank_code':
            # 跳过必填校验（bank_code 由系统自动填充，前端也是 readonly）
            continue
        
        # 其他字段 - 统一处理成字符串
        field_value = post_data.get(field_key)
        if isinstance(field_value, list):
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
        
        # 格式校验
        str_value = field_value
        
        # 长度校验
        if field.max_length and len(str_value) > field.max_length:
            errors[field_key] = f'{field.field_label}不能超过{field.max_length}个字符'
            continue
        
        # 根据 field_type 进行格式校验
        if field.field_type == 'phone' or field.validation_rule == 'phone':
            try:
                from apply.utils.applicant_validate import clean_cn_mobile
                clean_cn_mobile(str_value)
            except Exception as e:
                errors[field_key] = str(e)
        elif field.field_type == 'id_card':
            try:
                from apply.utils.applicant_validate import clean_id_card_18
                clean_id_card_18(str_value)
            except Exception as e:
                errors[field_key] = str(e)
        elif field.field_type == 'name' or field.validation_rule == 'name':
            # 姓名格式校验：至少2个汉字，最多15个汉字，少数民族·后需≥2个汉字，只能输入汉字
            chinese_chars = str_value.replace('·', '')
            chinese_count = len([c for c in chinese_chars if '\u4e00' <= c <= '\u9fff'])
            dot_parts = str_value.split('·')
            for i in range(1, len(dot_parts)):
                part_chinese = [c for c in dot_parts[i] if '\u4e00' <= c <= '\u9fff']
                if len(part_chinese) < 2:
                    errors[field_key] = '间隔符"·"后至少需要2个汉字'
                    break
            else:
                if chinese_count < 2:
                    errors[field_key] = '姓名须至少包含2个汉字'
                elif chinese_count > 15:
                    errors[field_key] = '姓名不能超过15个汉字'
                elif not all('\u4e00' <= c <= '\u9fff' or c == '·' for c in str_value):
                    errors[field_key] = '姓名只能输入汉字'
        elif field.field_type == 'amount' or field.validation_rule == 'amount_range':
            try:
                amount_str = str_value.replace(',', '').strip()
                Decimal(amount_str)
                if product:
                    amount = Decimal(amount_str)
                    lo, hi = product.credit_limit_min, product.credit_limit_max
                    if amount < lo or amount > hi:
                        errors[field_key] = f'申请金额必须在{lo:,.2f}～{hi:,.2f}元之间'
            except Exception:
                errors[field_key] = '请输入有效的金额数字'
        elif field.field_type == 'number' and not field.validation_rule:
            try:
                float(str_value)
            except (ValueError, TypeError):
                errors[field_key] = f'{field.field_label}必须为有效数字'
        elif field.field_type == 'date':
            import datetime
            try:
                if len(str_value) == 8:
                    datetime.datetime.strptime(str_value, '%Y%m%d')
                else:
                    datetime.datetime.strptime(str_value, '%Y-%m-%d')
            except (ValueError, TypeError):
                errors[field_key] = f'{field.field_label}日期格式不正确'
    
    return errors


@login_required  # 编辑需登录
@require_http_methods(["GET", "POST"])  # 允许 GET 展示 POST 保存
def return_edit_view(request, pk: int):  # 定义退回补充编辑视图
    """仅在退回状态下允许修改资料并回到待初审。"""  # 视图文档字符串
    application = get_object_or_404(Application.objects.select_related("bank"), pk=pk)  # 获取申请并预取银行
    if not can_access_application(request.user, application):  # 判断是否有权访问该申请
        messages.error(request, "无权操作该申请")  # 提示越权
        return redirect("apply:my_applications")  # 返回列表
    if application.status != Application.ST_RETURNED:  # 判断状态是否为退回补充
        messages.warning(request, "当前状态不可补充资料")  # 提示状态不符
        return redirect("apply:my_applications")  # 返回列表
    if request.method == "POST":  # 处理保存提交
        print(f"[DEBUG return_edit] ===== POST 请求开始 =====")
        print(f"[DEBUG return_edit] pk={pk}, application.status={application.status}")
        
        # ========== 动态表单字段后端校验 ==========
        from apply.models.form_config import FormPage, FormField
        from apply.views.multi_step_form import _validate_step_data
        
        # 获取所有动态字段配置（用于校验）
        form_pages_config = FormPage.objects.filter(is_active=True).prefetch_related('fields').order_by('order')
        
        # 获取第一页（基本信息页），退回编辑模式下跳过其必填校验
        first_page = form_pages_config.first()
        
        # 初始化 form_data（用于校验函数检查已有图片等）
        form_data = dict(application.form_data or {})
        
        all_errors = {}
        for page in form_pages_config:
            # 收集当前页的所有字段用于校验
            page_fields = list(page.fields.filter(is_active=True).order_by('sort_order'))
            if page_fields:
                print(f"[DEBUG return_edit] 校验页面: {page.page_title}, 字段数: {len(page_fields)}")
                
                # 判断是否为第一页（基本信息页）- 退回编辑模式下跳过必填校验
                is_basic_page = (page.pk == first_page.pk) if first_page else False
                
                # 对第一页的字段进行校验，但跳过必填校验（因为是只读字段）
                if is_basic_page:
                    # 只校验格式，不校验必填
                    for field in page_fields:
                        field_key = field.field_key
                        field_value = request.POST.get(field_key, '').strip()
                        
                        # 跳过核心字段和姓名拼音
                        if field_key in {'applicant_name', 'id_card', 'phone', 'amount', 'card_product', 'supplementary_note', 'return_reason', 'applicant_name_pinyin'}:
                            continue
                        if field.field_type == 'name_pinyin':
                            continue
                        
                        # 只读字段不校验必填
                        if field_value:
                            # 有值时进行格式校验
                            if field.field_type == 'phone':
                                try:
                                    from django.core.validators import validate_slug
                                    from apply.utils.validators import clean_cn_mobile
                                    clean_cn_mobile(field_value)
                                except Exception as e:
                                    all_errors[field_key] = str(e)
                            elif field.field_type == 'id_card':
                                try:
                                    from apply.utils.validators import clean_id_card_18
                                    clean_id_card_18(field_value)
                                except Exception as e:
                                    all_errors[field_key] = str(e)
                else:
                    # 非第一页正常校验，但退回编辑模式下跳过图片和银行栏的必填校验
                    page_errors = _validate_page_for_return_edit(page_fields, request.POST, form_data, product=application.card_product)
                    if page_errors:
                        all_errors.update(page_errors)
                        print(f"[DEBUG return_edit] 页面 {page.page_title} 校验失败: {page_errors}")
                    else:
                        print(f"[DEBUG return_edit] 页面 {page.page_title} 校验通过")
        
        print(f"[DEBUG return_edit] 所有校验错误: {all_errors}")
        
        # 如果有校验错误，返回表单并显示错误
        if all_errors:
            form = ReturnEditForm(instance=application)
            # 保留用户输入的动态字段值
            form_data = dict(application.form_data or {})
            first_page = FormPage.objects.filter(is_active=True).order_by('order').first()
            for page in form_pages_config:
                for field in page.fields.filter(is_active=True).order_by('sort_order'):
                    if field.field_key in {'applicant_name', 'id_card', 'phone', 'amount', 'card_product', 'supplementary_note', 'return_reason', 'applicant_name_pinyin'}:
                        continue
                    is_basic_readonly = (page.pk == first_page.pk) if first_page else False
                    field_value = request.POST.get(field.field_key)
                    if is_basic_readonly and not field_value:
                        field_value = form_data.get(field.field_key)
                    if field.field_type == 'checkbox':
                        checkbox_values = request.POST.getlist(field.field_key)
                        if checkbox_values:
                            field_value = ','.join(checkbox_values)
                        elif is_basic_readonly:
                            field_value = form_data.get(field.field_key)
                    base64_value = request.POST.get(f'{field.field_key}_base64')
                    if base64_value is not None and base64_value:
                        field_value = base64_value
                    if field_value:
                        form_data[field.field_key] = field_value
            return render(request, "return_edit.html", {
                "form": form,
                "application": application,
                "form_pages": form_pages_config,
                "form_data": form_data,
                "errors": all_errors,
            })
        # ========== 动态表单字段后端校验结束 ==========
        
        form = ReturnEditForm(request.POST, instance=application)  # 绑定实例
        if form.is_valid():  # 校验表单
            print(f"[DEBUG return_edit] ReturnEditForm 校验通过")
            obj = form.save(commit=False)  # 生成待保存对象

            # 保存动态字段到 form_data
            dynamic_data = dict(application.form_data or {})  # 保留原有数据
            
            # 获取第一页（基本信息页）用于判断只读字段
            first_page = FormPage.objects.filter(is_active=True).order_by('order').first()
            
            for page in FormPage.objects.filter(is_active=True).order_by('order'):
                for field in page.fields.filter(is_active=True).order_by('sort_order'):
                    # 跳过核心字段和只读字段
                    if field.field_key in {'applicant_name', 'id_card', 'phone', 'amount', 'card_product', 'supplementary_note', 'return_reason', 'applicant_name_pinyin'}:
                        continue
                    
                    # 判断是否为第一页（基本信息页）的只读字段
                    is_basic_readonly = (page.pk == first_page.pk) if first_page else False
                    
                    # 从 POST 获取动态字段值
                    field_value = request.POST.get(field.field_key)
                    
                    # 如果是只读字段（下拉框、单选框、复选框disabled后值不提交），从原有数据恢复
                    if is_basic_readonly and not field_value:
                        field_value = dynamic_data.get(field.field_key)
                    
                    # 处理复选框（多个同名字段）
                    if field.field_type == 'checkbox':
                        checkbox_values = request.POST.getlist(field.field_key)
                        if checkbox_values:
                            field_value = ','.join(checkbox_values)
                        elif is_basic_readonly:
                            # 只读复选框也从原有数据恢复
                            field_value = dynamic_data.get(field.field_key)
                    
                    # 处理图片 base64
                    base64_value = request.POST.get(f'{field.field_key}_base64')
                    if base64_value is not None:
                        field_value = base64_value if base64_value else None
                    
                    # 保存非空值
                    if field_value:
                        dynamic_data[field.field_key] = field_value
                    # 如果字段为空但存在于 form_data，删除它（允许清空）
                    elif field.field_key in dynamic_data:
                        del dynamic_data[field.field_key]

            obj.form_data = dynamic_data

            # 同步 AMOUNT 到 application.amount（与 _save_return_application 保持一致）
            amount_str = dynamic_data.get('AMOUNT') or dynamic_data.get('amount')
            if amount_str:
                try:
                    obj.amount = Decimal(amount_str.replace(',', '').strip())
                except Exception:
                    pass  # 保持原值

            obj.status = Application.ST_PENDING_FIRST  # 重置为待初审
            obj.return_reason = ""  # 清空退回原因
            print(f"[DEBUG return_edit] 保存前 - application.status={application.status}, form_data keys={list(dynamic_data.keys())}")
            obj.save()  # 持久化修改
            print(f"[DEBUG return_edit] 保存后 - application.status={application.status}")
            messages.success(request, "资料已更新并重新进入初审队列")  # 成功提示
            result = redirect("apply:my_applications")
            print(f"[DEBUG return_edit] ===== 完成，返回 redirect =====")
            return result
        else:
            print(f"[DEBUG return_edit] ReturnEditForm 校验失败: {form.errors}")
            # 表单验证失败，保留用户输入的动态字段值
            form_data = dict(application.form_data or {})
            from apply.models.form_config import FormPage
            first_page = FormPage.objects.filter(is_active=True).order_by('order').first()
            for page in FormPage.objects.filter(is_active=True).order_by('order'):
                for field in page.fields.filter(is_active=True).order_by('sort_order'):
                    if field.field_key in {'applicant_name', 'id_card', 'phone', 'amount', 'card_product', 'supplementary_note', 'return_reason', 'applicant_name_pinyin'}:
                        continue
                    # 判断是否为第一页的只读字段
                    is_basic_readonly = (page.pk == first_page.pk) if first_page else False
                    field_value = request.POST.get(field.field_key)
                    # 只读字段从原有数据恢复
                    if is_basic_readonly and not field_value:
                        field_value = form_data.get(field.field_key)
                    if field.field_type == 'checkbox':
                        checkbox_values = request.POST.getlist(field.field_key)
                        if checkbox_values:
                            field_value = ','.join(checkbox_values)
                        elif is_basic_readonly:
                            field_value = form_data.get(field.field_key)
                    base64_value = request.POST.get(f'{field.field_key}_base64')
                    if base64_value is not None and base64_value:
                        field_value = base64_value
                    if field_value:
                        form_data[field.field_key] = field_value
    else:  # GET 展示表单
        form = ReturnEditForm(instance=application)  # 绑定现有数据
        form_data = application.form_data or {}  # 初始化 form_data（确保变量存在）

    # 获取动态表单字段配置（用于公共模板）
    from apply.models.form_config import FormPage, FormField

    # 获取所有启用的表单页面（含字段配置）
    form_pages = FormPage.objects.filter(is_active=True).prefetch_related(
        Prefetch('fields', queryset=FormField.objects.filter(is_active=True).order_by('sort_order'))
    ).order_by('order')

    # 确保 form_data 变量存在（GET 或验证失败时）
    if 'form_data' not in dir() or form_data is None:
        form_data = application.form_data or {}

    # 为只读展示准备数据（按页面分组，有值才显示）
    raw_form_data = form_data  # 使用保留的用户输入值
    ordered_form_data = []  # 兼容旧模板
    for page in form_pages:
        page_fields = []
        for field in page.fields.all():
            # 跳过核心字段
            if field.field_key in {'applicant_name', 'id_card', 'phone', 'amount', 'card_product', 'supplementary_note', 'return_reason'}:
                continue
            value = raw_form_data.get(field.field_key)
            if not value:
                continue
            page_fields.append({
                'key': field.field_key,
                'label': field.field_label,
                'value': value,
                'type': field.field_type,
            })
        if page_fields:
            ordered_form_data.append({
                'page_title': page.page_title,
                'fields': page_fields,
            })

    return render(request, "return_edit.html", {
        "form": form,
        "application": application,
        "form_pages": form_pages,
        "form_data": form_data,
        "ordered_form_data": ordered_form_data,  # 保留兼容
    })


# ============================================================================
# 退回后完整编辑视图（复用多步骤表单）
# ============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def return_multi_step_view(request, pk: int):
    """
    退回状态下完整编辑表单视图。
    复用多步骤表单引擎，预填充已填写的数据，支持完整编辑。
    """
    from apply.models.form_config import FormPage, FormField
    from apply.views.multi_step_form import _get_form_pages, _validate_step_data

    application = get_object_or_404(
        Application.objects.select_related("bank", "card_product", "user"),
        pk=pk
    )

    if not can_access_application(request.user, application):
        messages.error(request, "无权操作该申请")
        return redirect("apply:my_applications")

    if application.status != Application.ST_RETURNED:
        messages.warning(request, "当前状态不可编辑")
        return redirect("apply:my_applications")

    product = application.card_product
    user_bank = application.bank

    # 获取表单页面配置
    form_pages = _get_form_pages()
    if not form_pages:
        messages.error(request, "暂无可用表单配置，请联系管理员")
        return redirect("apply:my_applications")

    # 获取现有的 form_data 作为预填充数据
    existing_form_data = application.form_data or {}

    # 核心字段映射（用于从 form_data 提取或回填）
    core_field_map = {
        'applicant_name': 'applicant_name',
        'id_card': 'id_card',
        'phone': 'phone',
        'AMOUNT': 'amount',  # 表单中的字段名
    }

    # 处理POST请求
    if request.method == "POST":
        print(f"[DEBUG] ===== POST 请求开始 =====")
        print(f"[DEBUG] pk={pk}, step={request.POST.get('step')}, is_last={request.POST.get('is_last')}")
        
        step = int(request.POST.get('step', 0))
        is_last = request.POST.get('is_last', 'false').lower() == 'true'
        is_prev = request.POST.get('prev_step') == '1'

        print(f"[DEBUG] step={step}, is_last={is_last}, is_prev={is_prev}, total_pages={len(form_pages)}")
        
        current_page = form_pages[step]
        page_fields = current_page['fields']
        print(f"[DEBUG] 当前页: {current_page['page'].page_title}, 字段数: {len(page_fields)}")

        # 获取当前页数据
        page_data = {}
        for field in page_fields:
            # 姓名拼音字段由系统自动生成
            if field.field_type == 'name_pinyin':
                name_field = next((f for f in page_fields if f.field_type == 'name' or f.validation_rule == 'name'), None)
                if name_field:
                    name_value = request.POST.get(name_field.field_key, '').strip()
                    if name_value:
                        from pypinyin import lazy_pinyin, Style
                        page_data[field.field_key] = ' '.join(lazy_pinyin(name_value, style=Style.NORMAL, strict=False)).upper()
                continue

            # 图片字段：优先使用 base64 数据
            if field.field_type == 'image':
                base64_value = request.POST.get(field.field_key + '_base64', '').strip()
                if base64_value:
                    page_data[field.field_key] = base64_value
                elif field.field_key in existing_form_data:
                    # 保留原有图片数据
                    page_data[field.field_key] = existing_form_data[field.field_key]
                continue

            field_value = request.POST.get(field.field_key, '').strip()
            page_data[field.field_key] = field_value

        # 上一步：保存数据并跳转
        if is_prev:
            existing_form_data.update(page_data)
            return redirect(f'{request.path}?step={step - 1}')

        # 校验当前页数据
        is_valid, errors = _validate_step_data(page_fields, request.POST, product=product)
        print(f"[DEBUG] 校验结果: is_valid={is_valid}, errors={errors}")

        if errors:
            existing_form_data.update(page_data)
            return render(request, "multi_step_form.html", {
                'product': product,
                'form_pages': form_pages,
                'current_page': current_page,
                'current_step': step,
                'page_data': existing_form_data,
                'is_last': is_last,
                'errors': errors,
            })

        # 保存当前页数据
        existing_form_data.update(page_data)

        # 如果是最后一步，保存
        if is_last:
            print(f"[DEBUG] 最后一步，准备保存数据，form_data keys: {list(existing_form_data.keys())}")
            result = _save_return_application(request, existing_form_data, product, application)
            print(f"[DEBUG] 保存完成，返回: {result}")
            return result
        else:
            print(f"[DEBUG] 跳转到下一步: step={step + 1}")
            return redirect(f'{request.path}?step={step + 1}')

    # GET请求 - 显示指定步骤的表单
    step = int(request.GET.get('step', 0))

    # 限制step范围
    if step < 0:
        step = 0
    if step >= len(form_pages):
        step = len(form_pages) - 1

    current_page = form_pages[step]
    is_last = (step == len(form_pages) - 1)

    # 如果是"银行专用栏"页面，自动注入银行号字段（只读）
    current_page_title = current_page['page'].page_title
    if '银行专用栏' in current_page_title:
        if 'bank_code' not in existing_form_data:
            existing_form_data['bank_code'] = product.bank.bank_code
        else:
            existing_form_data['bank_code'] = product.bank.bank_code

    return render(request, "multi_step_form.html", {
        'product': product,
        'form_pages': form_pages,
        'current_page': current_page,
        'current_step': step,
        'page_data': existing_form_data,
        'is_last': is_last,
        'errors': {},
        'is_return_edit': True,  # 标记为退回编辑模式
        'application': application,
    })


def _save_return_application(request, form_data, product, application):
    """
    保存退回编辑后的申请。
    核心字段更新到 Application，动态字段合并到 form_data。
    """
    print(f"[DEBUG] ===== _save_return_application 开始 =====")
    print(f"[DEBUG] application.id={application.pk}, product={product}")
    print(f"[DEBUG] form_data keys: {list(form_data.keys())}")
    
    from apply.models import Application

    # 【安全加固】强制用 product.bank.bank_code
    form_data['bank_code'] = product.bank.bank_code

    # 提取核心字段
    applicant_name = form_data.get('applicant_name', application.applicant_name)
    id_card = form_data.get('id_card', application.id_card).upper()  # 统一大写
    phone = form_data.get('phone', application.phone)
    # 兼容旧数据：form_data 中可能用 'AMOUNT'（大写）或 'amount'（小写）
    # 优先使用 AMOUNT（大写），因为原始申请数据都用大写
    amount_str = form_data.get('AMOUNT') or form_data.get('amount') or str(application.amount)

    # 处理金额
    try:
        amount_str = amount_str.replace(',', '').strip()
        amount = Decimal(amount_str)
    except Exception:
        amount = application.amount  # 保持原值

    # 获取补充说明（可能在前端表单中）
    supplementary_note = form_data.get('supplementary_note', application.supplementary_note or '')

    # 更新 Application 核心字段
    application.applicant_name = applicant_name
    application.id_card = id_card
    application.phone = phone
    application.amount = amount
    application.supplementary_note = supplementary_note

    # 如果更换了卡产品
    new_product_id = form_data.get('card_product_id')
    if new_product_id:
        try:
            from apply.models import CardProduct
            new_product = CardProduct.objects.get(pk=new_product_id, bank=product.bank)
            application.card_product = new_product
        except CardProduct.DoesNotExist:
            pass  # 保持原产品

    # 合并动态表单数据（保留原有图片等数据）
    existing_form_data = application.form_data or {}
    existing_form_data.update(form_data)

    # 确保银行号正确
    existing_form_data['bank_code'] = product.bank.bank_code

    application.form_data = existing_form_data

    # 重置状态
    application.status = Application.ST_PENDING_FIRST
    application.return_reason = ""

    print(f"[DEBUG] 保存前 - application.status={application.status}")
    application.save()
    print(f"[DEBUG] 保存后 - application.status={application.status}")

    messages.success(request, "资料已更新并重新进入初审队列")
    result = redirect("apply:my_applications")
    print(f"[DEBUG] ===== _save_return_application 完成，返回 redirect =====")
    return result


def _build_issue_compare(application: Application) -> list[dict]:  # 定义私有函数生成比对行
    """将发卡快照与原始字段对比并标记是否不一致。"""  # 函数文档字符串
    rows: list[dict] = []  # 初始化结果列表
    data = application.issue_data or {}  # 读取 JSON 快照缺省空字典
    orig_name = application.applicant_name  # 取出原始姓名
    iss_name = data.get("applicant_name", "")  # 取出快照姓名
    rows.append({"label": "姓名", "original": orig_name, "issued": iss_name, "mismatch": orig_name != iss_name})  # 追加一行
    orig_id = application.id_card  # 原始身份证
    iss_id = data.get("id_card", "")  # 快照身份证
    rows.append({"label": "身份证号", "original": orig_id, "issued": iss_id, "mismatch": orig_id != iss_id})  # 追加一行
    orig_amt = application.amount  # 原始 Decimal 额度
    iss_amt_raw = data.get("issue_amount")  # 快照额度可能是字符串
    try:  # 尝试将快照额度转 Decimal
        iss_amt = Decimal(str(iss_amt_raw)) if iss_amt_raw is not None else None  # 转换失败时变 None
    except Exception:  # 捕获任意转换异常
        iss_amt = None  # 标记为无法比较
    mismatch_amt = iss_amt is None or orig_amt != iss_amt  # 判断额度是否不一致
    rows.append({"label": "申请额度", "original": str(orig_amt), "issued": str(iss_amt_raw or ""), "mismatch": mismatch_amt})  # 追加额度行
    orig_prod = application.card_product.product_name if application.card_product_id else ""  # 原始产品名
    iss_prod = data.get("product_name", "")  # 快照产品名
    rows.append({"label": "卡种", "original": orig_prod, "issued": iss_prod, "mismatch": orig_prod != iss_prod})  # 追加卡种行
    # 比对动态表单字段
    orig_form_data = application.form_data or {}  # 原始动态表单数据
    iss_form_data = data.get("form_data", {})  # 快照动态表单数据
    if orig_form_data or iss_form_data:  # 有动态表单数据时
        from apply.models.form_config import FormField  # 延迟导入避免循环
        # 获取所有字段的标签映射和字段类型
        field_info = {f.field_key: {"label": f.field_label, "type": f.field_type} for f in FormField.objects.filter(is_active=True)}
        # 合并所有字段键
        all_keys = set(orig_form_data.keys()) | set(iss_form_data.keys())
        # 排除已在核心字段中比对的键
        exclude_keys = {"applicant_name", "id_card", "card_product", "amount", "bank_code"}

        def _is_image_field(val) -> bool:
            """判断字段值是否为图片数据（Base64 或 URL）"""
            if isinstance(val, list) and val:
                val = val[0]
            if isinstance(val, str):
                return val.startswith("data:image") or val.startswith("http")
            return False

        for key in sorted(all_keys):  # 按键名排序保证顺序一致
            if key in exclude_keys:
                continue  # 跳过已在核心字段中比对的键
            info = field_info.get(key, {})
            field_type = info.get("type", "")
            # 图片/文件字段跳过，不做比对
            if field_type in ("image", "file"):
                continue  # 跳过图片和文件字段
            orig_val = orig_form_data.get(key, "")
            iss_val = iss_form_data.get(key, "")
            # 图片字段跳过，不做比对
            if _is_image_field(orig_val) or _is_image_field(iss_val):
                continue  # 跳过图片字段
            # 文件/图片字段只显示是否有值
            if isinstance(orig_val, list) or isinstance(iss_val, list):
                orig_display = f"已上传{len(orig_val) if isinstance(orig_val, list) else 0}张" if orig_val else "未上传"
                iss_display = f"已上传{len(iss_val) if isinstance(iss_val, list) else 0}张" if iss_val else "未上传"
                mismatch = orig_display != iss_display
            else:
                orig_display = str(orig_val) if orig_val else ""
                iss_display = str(iss_val) if iss_val else ""
                mismatch = orig_display != iss_display
            label = info.get("label", key)  # 使用配置的标签， fallback 到键名
            rows.append({"label": label, "original": orig_display, "issued": iss_display, "mismatch": mismatch})
    return rows  # 返回完整比对列表


@login_required  # 详情需登录
@require_http_methods(["GET"])  # 详情仅展示
def application_detail_view(request, pk: int):  # 定义申请详情视图
    """展示完整信息并在已发卡时高亮不一致字段。"""  # 视图文档字符串
    application = get_object_or_404(Application.objects.select_related("bank", "card_product", "user"), pk=pk)  # 获取并预取
    if not can_access_application(request.user, application):  # 判断访问权限
        messages.error(request, "无权查看该申请")  # 越权提示
        return redirect("apply:home")  # 回首页

    # 获取动态表单配置
    from apply.models.form_config import FormPage

    form_pages = FormPage.objects.filter(is_active=True).order_by('order')

    form_data = application.form_data or {}

    compare_rows = []  # 默认无比对数据
    if application.status == Application.ST_ISSUED and application.issue_data:  # 已发卡且有快照时
        compare_rows = _build_issue_compare(application)  # 生成比对行数据
    return render(  # 渲染详情模板
        request,  # 请求对象
        "application_detail.html",  # 模板名
        {"application": application, "compare_rows": compare_rows, "form_pages": form_pages, "form_data": form_data},  # 上下文
    )
