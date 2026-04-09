/**
 * 拦截 method=post 的表单，在首次提交时弹出 Bootstrap 确认框（确认/取消）。
 * 表单可加 class「no-post-confirm」跳过；确认后通过 data 标记放行二次提交。
 */
(function () {
  const modalEl = document.getElementById("postSubmitConfirmModal"); // 获取模态框根节点
  if (!modalEl || typeof bootstrap === "undefined") {
    return; // 无模态或未加载 Bootstrap 时直接退出
  }
  const modal = new bootstrap.Modal(modalEl); // 实例化模态框控制器
  const okBtn = document.getElementById("postSubmitConfirmOk"); // 确认按钮
  if (!okBtn) {
    return; // 缺少按钮则不做绑定
  }
  let pendingForm = null; // 暂存待提交的表单引用
  okBtn.addEventListener("click", function () {
    modal.hide(); // 关闭弹窗
    if (pendingForm) {
      pendingForm.setAttribute("data-post-confirmed", "1"); // 标记已确认避免再次拦截
      if (typeof pendingForm.requestSubmit === "function") {
        pendingForm.requestSubmit(); // 标准方式再次触发表单提交
      } else {
        pendingForm.submit(); // 兼容旧浏览器的提交方式
      }
    }
    pendingForm = null; // 清空引用
  });
  document.addEventListener(
    "submit",
    async function (e) {
      const form = e.target; // 事件目标应为表单元素
      if (!form || form.tagName !== "FORM" || form.method.toLowerCase() !== "post") {
        return; // 非 POST 表单不处理
      }
      // 获取触发提交的按钮
      const submittedBtn = e.submitter;
      // 如果有确认标记，说明是弹窗确认后的二次提交，放行
      if (form.getAttribute("data-post-confirmed") === "1") {
        form.removeAttribute("data-post-confirmed"); // 清除标记以便下次仍可确认
        return; // 放行真实提交
      }
      // 只有按钮有 post-confirm 类才弹窗
      if (!submittedBtn || !submittedBtn.classList.contains("post-confirm")) {
        return; // 没有 post-confirm 类，跳过
      }
      // 【前置必填校验】：调用表单的 validateFormOnSubmit 进行完整校验
      // validateFormOnSubmit 是 async 函数，需要 await 获取结果
      if (typeof validateFormOnSubmit === "function") {
        e.preventDefault(); // 先阻止，校验通过后再手动提交
        var valid = await validateFormOnSubmit(form);
        if (!valid) {
          return; // 校验失败，已在 validateFormOnSubmit 中处理错误提示
        }
        // 校验通过，保存表单引用并显示确认弹窗
        pendingForm = form;
        modal.show();
        return;
      }
      e.preventDefault(); // 阻止首次直接提交
      e.stopPropagation(); // 避免冒泡触发其它逻辑
      pendingForm = form; // 记录待确认表单
      modal.show(); // 展示确认弹窗
    },
    true,
  ); // 使用捕获阶段优先于默认校验
})();
