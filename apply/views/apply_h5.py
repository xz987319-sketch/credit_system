"""H5 进件视图：无需登录的移动端申请表单处理。"""  # 模块文档字符串
from django.contrib import messages  # 导入消息框架提示提交结果
from django.shortcuts import get_object_or_404, redirect, render  # 导入快捷函数
from django.views.decorators.http import require_http_methods  # 导入 HTTP 方法限制装饰器

from apply.forms import H5ApplyForm  # 导入 H5 申请表单
from apply.models import Application, Bank, CardProduct  # 导入业务模型


# =============================================================================
# 银行大厅 → 卡种列表 → 卡种详情 → 申请表单
# =============================================================================

@require_http_methods(["GET"])  # 仅允许 GET 请求
def bank_hall(request):  # 银行大厅视图
    """展示所有银行的热门信用卡，支持按银行筛选。"""
    # 获取所有有启用卡产品的银行
    banks = Bank.objects.filter(
        card_products__is_active=True
    ).distinct().select_related().order_by("-is_featured", "bank_code")
    
    # 为每个银行获取热门卡片（最多2张）
    banks_with_cards = []
    for bank in banks:
        featured_cards = bank.get_featured_products(limit=2)
        all_cards = bank.get_active_products()
        banks_with_cards.append({
            "bank": bank,
            "featured_cards": list(featured_cards),
            "total_count": all_cards.count(),
        })
    
    return render(request, "bank_hall.html", {"banks": banks_with_cards})


@require_http_methods(["GET"])  # 仅允许 GET 请求
def bank_card_list(request, bank_id: int):  # 某银行下的卡种列表
    """展示指定银行的所有可申请信用卡产品。"""
    bank = get_object_or_404(Bank, pk=bank_id)  # 获取指定银行
    products = bank.get_active_products()  # 获取该银行所有启用中的卡产品
    return render(request, "bank_card_list.html", {"products": products, "bank": bank})


@require_http_methods(["GET"])  # 仅允许 GET 请求
def card_product_list(request):  # 卡种列表页视图（兼容重定向到银行大厅）
    """展示所有可申请的信用卡产品列表（兼容旧链接）。"""
    return redirect("apply:bank_hall")


@require_http_methods(["GET"])  # 仅允许 GET 请求
def card_product_detail(request, pk: int):  # 卡种详情页视图
    """展示单个卡产品的详细信息（产品特点、要点、资料、注意事项）。"""
    product = get_object_or_404(CardProduct, pk=pk, is_active=True)  # 获取指定卡产品
    return render(request, "card_product_detail.html", {"product": product})  # 渲染卡种详情模板


@require_http_methods(["GET"])  # 仅允许 GET 请求
def card_product_detail(request, pk: int):  # 卡种详情页视图
    """展示单个卡产品的详细信息（产品特点、要点、资料、注意事项）。"""
    product = get_object_or_404(CardProduct, pk=pk, is_active=True)  # 获取指定卡产品
    return render(request, "card_product_detail.html", {"product": product})  # 渲染卡种详情模板


@require_http_methods(["GET", "POST"])  # 允许 GET 展示 POST 提交
def h5_apply_view(request, product_id=None):  # H5 申请视图（支持指定卡种）
    """读取演示银行启用卡产品并创建待初审申请记录。"""
    demo_bank = get_object_or_404(Bank, bank_code="0000")  # 获取演示银行不存在则 404
    products = CardProduct.objects.filter(bank=demo_bank, is_active=True)  # 查询该行启用中的卡产品

    # 处理 GET 请求：展示申请表单
    if request.method == "GET":
        form = H5ApplyForm(card_queryset=products)  # 展示空表单
        # 如果指定了 product_id，预选卡产品
        if product_id:
            selected_product = products.filter(pk=product_id).first()  # 查找指定卡产品
            if selected_product:
                form.fields["card_product"].initial = selected_product  # 设置初始值
        return render(request, "apply_h5.html", {"form": form})  # 渲染 H5 模板

    # 处理 POST 请求：提交申请
    form = H5ApplyForm(request.POST, card_queryset=products)  # 绑定 POST 与受限查询集
    if product_id:  # 如果从卡种详情页进入且校验失败，保持卡种预选
        selected_product = products.filter(pk=product_id).first()
        if selected_product:
            form.fields["card_product"].initial = selected_product  # 保持初始值
    if form.is_valid():  # 执行字段与联合校验
        app = form.save(commit=False)  # 生成未落库的申请实例
        app.bank = demo_bank  # 强制关联演示银行
        app.user = None  # H5 进件不绑定内部员工
        app.status = Application.ST_PENDING_FIRST  # 设置初始状态为待初审
        app.save()  # 写入数据库生成主键
        # H5 专用成功页面：只显示关闭按钮，无返回和倒计时
        return render(request, "apply_h5_success.html", {"application": app})
    else:  # 校验失败
        messages.error(request, "请根据提示修正表单")  # 提示修正错误
        return render(request, "apply_h5.html", {"form": form})  # 重新渲染表单


@require_http_methods(["GET"])  # 成功页仅展示
def apply_success_view(request, pk: int):  # 定义成功页视图
    """展示刚创建的申请主键作为申请编号。"""  # 视图文档字符串
    app = get_object_or_404(Application, pk=pk)  # 按主键获取申请防止伪造
    return render(request, "apply_success.html", {"application": app})  # 渲染成功模板
