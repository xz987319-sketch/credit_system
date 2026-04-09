"""审核员视图：初审与复审队列及通过退回操作。"""  # 模块文档字符串
from django.contrib import messages  # 导入消息框架
from django.contrib.auth.decorators import login_required  # 导入登录装饰器
from django.core.paginator import Paginator  # 导入分页器
from django.db.models import Q  # 导入 Q 对象组合查询条件
from django.shortcuts import get_object_or_404, redirect, render  # 导入快捷函数
from django.utils import timezone  # 导入时区工具写入时间戳
from django.views.decorators.http import require_http_methods, require_POST  # 导入方法限制装饰器

from apply.forms import ReasonForm  # 导入原因表单
from apply.models import Application, CardProduct  # 导入申请模型和卡产品模型
from apply.utils.bank_scope import scope_by_bank  # 导入银行范围过滤
from apply.views.access import can_access_application, can_access_auditor_functions  # 导入权限辅助
from apply.models.form_config import FormPage  # 导入表单配置


def _deny_if_not_qi(request):  # 定义内部函数处理无初审复审权限的访问
    """非超级管理员且非银行审核员则提示并重定向首页。"""  # 函数文档字符串
    if not can_access_auditor_functions(request.user):  # 判断是否为超管或审核员
        messages.error(request, "需要银行审核员或超级管理员权限")  # 提示权限不足
        return redirect("apply:home")  # 返回首页
    return None  # 返回 None 表示校验通过


@login_required  # 列表需登录
@require_http_methods(["GET"])  # 仅 GET 展示
def pending_first_list_view(request):  # 初审待办列表
    """展示本行待初审申请并分页，支持姓名/身份证/手机号搜索和卡种筛选。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 校验审核员角色
    if maybe:  # 若返回重定向则直接返回
        return maybe  # 结束请求

    # 获取当前用户的银行范围
    user_bank = getattr(request.user, 'bank', None)

    qs = scope_by_bank(Application.objects.select_related("card_product", "bank"), request.user)  # 过滤本行数据
    qs = qs.filter(status=Application.ST_PENDING_FIRST)  # 仅保留待初审状态

    # 搜索：姓名、身份证或手机号
    keyword = (request.GET.get("q") or "").strip()
    if keyword:
        qs = qs.filter(
            Q(applicant_name__icontains=keyword) |
            Q(id_card__icontains=keyword) |
            Q(phone__icontains=keyword)
        )

    # 卡种筛选
    card_product_id = (request.GET.get("card_product") or "").strip()
    if card_product_id:
        qs = qs.filter(card_product_id=card_product_id)

    # 根据用户权限获取卡种列表供下拉选择
    if request.user.is_superuser:
        # 超级管理员可筛选所有银行的卡种
        card_products = CardProduct.objects.filter(is_active=True).order_by("bank__bank_name", "product_name")
    else:
        # 银行审核员仅能筛选本行的卡种
        card_products = CardProduct.objects.filter(bank=user_bank, is_active=True).order_by("product_name")

    paginator = Paginator(qs.order_by("-created_at"), 10)  # 按创建时间倒序分页（最新在前）
    page_obj = paginator.get_page(request.GET.get("page"))  # 当前页
    return render(request, "pending_list.html", {
        "page_obj": page_obj,
        "keyword": keyword,
        "card_products": card_products,
        "card_product_id": card_product_id,
    })  # 渲染模板


@login_required  # 详情需登录
@require_http_methods(["GET"])  # 仅 GET 展示
def pending_first_detail_view(request, pk: int):  # 初审详情视图
    """展示申请详情供初审人员审核。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 角色校验
    if maybe:  # 若失败
        return maybe  # 返回
    application = get_object_or_404(Application, pk=pk)  # 获取申请
    if not can_access_application(request.user, application):  # 隔离校验
        messages.error(request, "无权查看")  # 提示
        return redirect("apply:pending_first")  # 回列表

    # 获取动态表单配置
    form_pages = FormPage.objects.filter(is_active=True).order_by('order')
    form_data = application.form_data or {}

    return render(request, "pending_first_review.html", {
        "application": application,
        "form_pages": form_pages,
        "form_data": form_data,
        "show_actions": True,
    })


@login_required  # 详情需登录
@require_http_methods(["GET"])  # 仅 GET 展示
def pending_second_detail_view(request, pk: int):  # 复审详情视图
    """展示申请详情供复审人员审核。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 角色校验
    if maybe:  # 若失败
        return maybe  # 返回
    application = get_object_or_404(Application, pk=pk)  # 获取申请
    if not can_access_application(request.user, application):  # 隔离校验
        messages.error(request, "无权查看")  # 提示
        return redirect("apply:pending_second")  # 回列表

    # 获取动态表单配置
    form_pages = FormPage.objects.filter(is_active=True).order_by('order')
    form_data = application.form_data or {}

    return render(request, "pending_second_review.html", {
        "application": application,
        "form_pages": form_pages,
        "form_data": form_data,
        "show_actions": True,
    })


@login_required  # 操作需登录
@require_POST  # 仅允许 POST 防止 CSRF GET（仍需 CSRF token）
def pending_first_pass_view(request, pk: int):  # 初审通过视图
    """将申请置为待复审并记录初审通过时间。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 角色校验
    if maybe:  # 不通过则返回
        return maybe  # 提前返回
    application = get_object_or_404(Application, pk=pk)  # 获取申请
    if not can_access_application(request.user, application):  # 银行隔离校验
        messages.error(request, "无权操作")  # 提示错误
        return redirect("apply:pending_first")  # 回列表
    if application.status != Application.ST_PENDING_FIRST:  # 校验状态
        messages.warning(request, "状态已变化")  # 提示冲突
        return redirect("apply:pending_first")  # 回列表
    application.status = Application.ST_PENDING_SECOND  # 更新为待复审
    application.init_audit_time = timezone.now()  # 写入初审通过时间
    application.save(update_fields=["status", "init_audit_time", "updated_at"])  # 保存字段子集
    messages.success(request, "初审已通过")  # 成功提示
    return redirect("apply:pending_first")  # 返回列表


@login_required  # 退回需登录
@require_http_methods(["GET", "POST"])  # GET 展示 POST 提交
def pending_first_return_view(request, pk: int):  # 初审退回视图
    """填写退回原因并将状态改为退回补充。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 角色校验
    if maybe:  # 若不通过
        return maybe  # 返回重定向
    application = get_object_or_404(Application, pk=pk)  # 获取申请
    if not can_access_application(request.user, application):  # 隔离校验
        messages.error(request, "无权操作")  # 提示
        return redirect("apply:pending_first")  # 回列表
    if application.status != Application.ST_PENDING_FIRST:  # 状态检查
        messages.warning(request, "状态已变化")  # 提示
        return redirect("apply:pending_first")  # 回列表
    if request.method == "POST":  # 处理提交
        form = ReasonForm(request.POST)  # 绑定原因表单
        if form.is_valid():  # 校验原因
            application.status = Application.ST_RETURNED  # 标记退回补充
            application.return_reason = form.cleaned_data["reason"]  # 保存退回说明
            application.save(update_fields=["status", "return_reason", "updated_at"])  # 持久化
            messages.success(request, "已退回补充资料")  # 提示成功
            return redirect("apply:pending_first")  # 回列表
    else:  # GET
        form = ReasonForm()  # 空表单
    return render(request, "audit_reject.html", {"form": form, "application": application})  # 渲染退回页


@login_required  # 复审列表需登录
@require_http_methods(["GET"])  # 仅 GET
def pending_second_list_view(request):  # 复审待办列表
    """展示本行待复审申请分页列表，支持姓名/身份证/手机号搜索和卡种筛选。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 角色校验
    if maybe:  # 若失败
        return maybe  # 返回

    # 获取当前用户的银行范围
    user_bank = getattr(request.user, 'bank', None)

    qs = scope_by_bank(Application.objects.select_related("card_product", "bank"), request.user)  # 本行
    qs = qs.filter(status=Application.ST_PENDING_SECOND)  # 待复审

    # 搜索：姓名、身份证或手机号
    keyword = (request.GET.get("q") or "").strip()
    if keyword:
        qs = qs.filter(
            Q(applicant_name__icontains=keyword) |
            Q(id_card__icontains=keyword) |
            Q(phone__icontains=keyword)
        )

    # 卡种筛选
    card_product_id = (request.GET.get("card_product") or "").strip()
    if card_product_id:
        qs = qs.filter(card_product_id=card_product_id)

    # 根据用户权限获取卡种列表供下拉选择
    if request.user.is_superuser:
        # 超级管理员可筛选所有银行的卡种
        card_products = CardProduct.objects.filter(is_active=True).order_by("bank__bank_name", "product_name")
    else:
        # 银行审核员仅能筛选本行的卡种
        card_products = CardProduct.objects.filter(bank=user_bank, is_active=True).order_by("product_name")

    paginator = Paginator(qs.order_by("-init_audit_time"), 10)  # 按初审时间倒序分页（最新在前）
    page_obj = paginator.get_page(request.GET.get("page"))  # 当前页
    return render(request, "second_pending_list.html", {
        "page_obj": page_obj,
        "keyword": keyword,
        "card_products": card_products,
        "card_product_id": card_product_id,
    })  # 渲染


@login_required  # 复审通过
@require_POST  # POST 提交
def pending_second_pass_view(request, pk: int):  # 复审通过进入信审
    """将状态更新为信审中。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 角色
    if maybe:  # 失败返回
        return maybe  # 返回
    application = get_object_or_404(Application, pk=pk)  # 查询申请
    if not can_access_application(request.user, application):  # 隔离
        messages.error(request, "无权操作")  # 提示
        return redirect("apply:pending_second")  # 回列表
    if application.status != Application.ST_PENDING_SECOND:  # 状态
        messages.warning(request, "状态已变化")  # 提示
        return redirect("apply:pending_second")  # 回列表
    application.status = Application.ST_CREDIT_ING  # 进入信审
    application.second_audit_time = timezone.now()  # 记录复审通过时间
    application.save(update_fields=["status", "second_audit_time", "updated_at"])  # 保存
    messages.success(request, "复审已通过，已进入信审")  # 提示
    return redirect("apply:pending_second")  # 回列表


@login_required  # 复审拒绝
@require_http_methods(["GET", "POST"])  # 表单页
def pending_second_reject_view(request, pk: int):  # 复审拒绝视图
    """填写拒绝原因并终止流程。"""  # 视图文档字符串
    maybe = _deny_if_not_qi(request)  # 角色
    if maybe:  # 失败
        return maybe  # 返回
    application = get_object_or_404(Application, pk=pk)  # 查询
    if not can_access_application(request.user, application):  # 隔离
        messages.error(request, "无权操作")  # 提示
        return redirect("apply:pending_second")  # 回列表
    if application.status != Application.ST_PENDING_SECOND:  # 状态
        messages.warning(request, "状态已变化")  # 提示
        return redirect("apply:pending_second")  # 回列表
    if request.method == "POST":  # 提交
        form = ReasonForm(request.POST)  # 绑定
        if form.is_valid():  # 校验
            application.status = Application.ST_SECOND_REJECT  # 复审拒绝终止
            application.second_reject_reason = form.cleaned_data["reason"]  # 写入复审拒绝专用字段
            application.save(update_fields=["status", "second_reject_reason", "updated_at"])  # 保存
            messages.success(request, "已拒绝该申请")  # 提示
            return redirect("apply:pending_second")  # 回列表
    else:  # GET
        form = ReasonForm()  # 空表单
    return render(request, "second_audit_reject.html", {"form": form, "application": application})  # 渲染
