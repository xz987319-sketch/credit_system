"""超级管理员业务视图：信审待办与发卡或拒绝操作。"""  # 模块文档字符串
from django.contrib import messages  # 导入消息框架
from django.contrib.auth.decorators import login_required  # 导入登录装饰器
from django.core.paginator import Paginator  # 导入分页器
from django.db.models import Q  # 导入 Q 对象组合查询条件
from django.shortcuts import get_object_or_404, redirect, render  # 导入快捷函数
from django.utils import timezone  # 导入时区工具
from django.views.decorators.http import require_http_methods, require_POST  # 导入 HTTP 限制

from apply.forms import ReasonForm  # 导入原因表单
from apply.models import Application, AuditLog, CardProduct  # 导入申请模型和卡产品模型
from apply.models.form_config import FormPage  # 导入表单配置


def _deny_if_not_superuser(request):  # 内部超级用户校验
    """非超级管理员则提示并重定向首页。"""  # 文档字符串
    if not request.user.is_superuser:  # 判断标志位
        messages.error(request, "需要超级管理员权限")  # 提示
        return redirect("apply:home")  # 回首页
    return None  # 通过


@login_required  # 列表需登录
@require_http_methods(["GET"])  # 仅展示
def credit_pending_list_view(request):  # 信审待办列表
    """展示所有银行处于信审中的申请，支持姓名/身份证/手机号搜索和卡种筛选。"""  # 视图文档字符串
    maybe = _deny_if_not_superuser(request)  # 校验超级用户
    if maybe:  # 若失败
        return maybe  # 返回

    qs = Application.objects.select_related("bank", "card_product").filter(status=Application.ST_CREDIT_ING)  # 查询信审中

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

    # 获取所有启用的卡种列表供下拉选择
    card_products = CardProduct.objects.filter(is_active=True).order_by("bank__bank_name", "product_name")

    paginator = Paginator(qs.order_by("-created_at"), 10)  # 按创建时间倒序分页（最新在前）
    page_obj = paginator.get_page(request.GET.get("page"))  # 当前页
    return render(request, "credit_pending_list.html", {
        "page_obj": page_obj,
        "keyword": keyword,
        "card_products": card_products,
        "card_product_id": card_product_id,
    })  # 渲染


@login_required  # 详情需登录
@require_http_methods(["GET"])  # 仅 GET 展示
def credit_pending_detail_view(request, pk: int):  # 信审详情视图
    """展示申请详情供信审人员审核。"""  # 视图文档字符串
    maybe = _deny_if_not_superuser(request)  # 校验超级用户
    if maybe:  # 若失败
        return maybe  # 返回
    application = get_object_or_404(Application, pk=pk)  # 获取申请

    # 获取动态表单配置
    form_pages = FormPage.objects.filter(is_active=True).order_by('order')
    form_data = application.form_data or {}

    return render(request, "credit_pending_review.html", {
        "application": application,
        "form_pages": form_pages,
        "form_data": form_data,
        "show_actions": True,
    })


@login_required  # 发卡需登录
@require_POST  # POST 触发
def credit_pass_view(request, pk: int):  # 信审通过发卡
    """生成虚拟卡号并写入 JSON 快照。"""  # 视图文档字符串
    maybe = _deny_if_not_superuser(request)  # 校验
    if maybe:  # 失败
        return maybe  # 返回
    application = get_object_or_404(Application.objects.select_related("card_product"), pk=pk)  # 获取并预取产品
    if application.status != Application.ST_CREDIT_ING:  # 状态必须为信审中
        messages.warning(request, "状态已变化")  # 提示
        return redirect("apply:credit_pending")  # 回列表
    card_number = f"6222{str(application.pk).zfill(12)}"  # 构造 16 位虚拟卡号
    now = timezone.now()  # 获取当前时间戳
    previous_status = application.status  # 记录操作前状态
    application.card_number = card_number  # 写入卡号字段
    application.status = Application.ST_ISSUED  # 标记已发卡
    application.credit_time = now  # 记录信审结束时间
    application.credit_audit_time = now  # 记录信审通过时间
    application.issued_time = now  # 记录已发卡时间
    application.issue_data = {  # 组装 JSON 快照字典
        "card_number": card_number,  # 卡号
        "issue_amount": str(application.amount),  # 发卡额度字符串化
        "issue_date": now.date().isoformat(),  # 发卡日期 ISO 格式
        "applicant_name": application.applicant_name,  # 姓名快照
        "id_card": application.id_card,  # 证件快照
        "product_name": application.card_product.product_name,  # 卡种名称快照
        "form_data": dict(application.form_data or {}),  # 动态表单数据快照
    }
    application.save()  # 持久化所有变更字段
    # 写入审核记录
    AuditLog.objects.create(
        application=application,
        auditor=request.user,
        audit_type=AuditLog.TYPE_CREDIT,
        result="信审通过",
        previous_status=previous_status,
        new_status=Application.ST_ISSUED,
        comment=f"虚拟发卡，卡号：{card_number}",
    )
    messages.success(  # 成功提示并带上卡号便于核对
        request,  # 请求对象
        f"信审通过并完成虚拟发卡，卡号：{card_number}，可在申请详情中查看完整发卡信息。",  # 含卡号文案
    )
    return redirect("apply:application_detail", pk=application.pk)  # 跳转详情页展示卡号与快照


@login_required  # 拒绝需登录
@require_http_methods(["GET", "POST"])  # 展示与提交
def credit_reject_view(request, pk: int):  # 信审拒绝视图
    """记录拒绝原因并终止流程。"""  # 视图文档字符串
    maybe = _deny_if_not_superuser(request)  # 校验
    if maybe:  # 失败
        return maybe  # 返回
    application = get_object_or_404(Application, pk=pk)  # 获取申请
    if application.status != Application.ST_CREDIT_ING:  # 状态检查
        messages.warning(request, "状态已变化")  # 提示
        return redirect("apply:credit_pending")  # 回列表
    if request.method == "POST":  # 提交拒绝
        form = ReasonForm(request.POST)  # 绑定表单
        if form.is_valid():  # 校验
            previous_status = application.status  # 记录操作前状态
            comment = form.cleaned_data["reason"]  # 获取拒绝原因
            application.status = Application.ST_REJECTED  # 标记信审拒绝
            application.credit_remark = comment  # 保存拒绝说明
            application.credit_time = timezone.now()  # 写入处理时间
            application.save(update_fields=["status", "credit_remark", "credit_time", "updated_at"])  # 更新字段
            # 写入审核记录
            AuditLog.objects.create(
                application=application,
                auditor=request.user,
                audit_type=AuditLog.TYPE_CREDIT,
                result="信审拒绝",
                previous_status=previous_status,
                new_status=Application.ST_REJECTED,
                comment=comment,
            )
            messages.success(request, "已拒绝该申请")  # 提示
            return redirect("apply:credit_pending")  # 回列表
    else:  # GET
        form = ReasonForm()  # 空表单
    return render(request, "credit_review.html", {"form": form, "application": application})  # 渲染拒绝页
