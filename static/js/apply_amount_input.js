/**
 * 申请金额：text 输入过滤、与卡种下拉联动提示、提交前校验（配合 Django 后端二次校验）。
 */
(function () {
  function fmtMoney(n) {
    var x = Number(n);
    if (!isFinite(x)) return String(n);
    return x.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function getSelectedProductMeta(selectEl) {
    if (!selectEl) return null;
    var opt = selectEl.options[selectEl.selectedIndex];
    if (!opt || !opt.value) return null;
    var mn = opt.getAttribute("data-credit-min");
    var mx = opt.getAttribute("data-credit-max");
    if (mn == null || mx == null) return null;
    return { min: parseFloat(mn), max: parseFloat(mx), label: opt.text.trim() };
  }

  function sanitizeAmountString(raw) {
    var s = String(raw || "");
    var out = "";
    var dot = false;
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (c >= "0" && c <= "9") {
        if (dot) {
          var frac = out.split(".")[1] || "";
          if (frac.length >= 2) continue;
        }
        out += c;
      } else if (c === ".") {
        if (!dot) {
          dot = true;
          if (out === "") out = "0";
          out += ".";
        }
      }
    }
    return out;
  }

  function parseAmountValue(s) {
    if (!s || !String(s).trim()) return { ok: false, code: "empty" };
    var t = String(s).trim();
    if (t.startsWith(".")) t = "0" + t;
    if (!/^\d+(\.\d{0,2})?$/.test(t)) {
      if (t.indexOf(".") >= 0 && t.split(".")[1].length > 2) return { ok: false, code: "decimals" };
      return { ok: false, code: "format" };
    }
    var v = parseFloat(t);
    if (!isFinite(v)) return { ok: false, code: "format" };
    if (v <= 0) return { ok: false, code: "nonpositive" };
    return { ok: true, value: v, text: t };
  }

  function validateAgainstProduct(v, meta) {
    if (!meta) return { ok: true };
    if (v < meta.min || v > meta.max) {
      return {
        ok: false,
        msg:
          "申请金额必须在 " + fmtMoney(meta.min) + " ～ " + fmtMoney(meta.max) + " 元之间。",
      };
    }
    return { ok: true };
  }

  function updateRangeHint(selectEl, hintEl) {
    if (!hintEl) return;
    var meta = getSelectedProductMeta(selectEl);
    if (!meta) {
      hintEl.textContent = "请先选择卡种，选择后将显示可申请金额范围。";
      return;
    }
    hintEl.textContent =
      "可申请金额范围：" + fmtMoney(meta.min) + " ～ " + fmtMoney(meta.max) + " 元";
  }

  function updateLiveFeedback(inputEl, selectEl, feedbackEl) {
    if (!feedbackEl) return;
    var meta = getSelectedProductMeta(selectEl);
    var raw = inputEl.value;
    var parsed = parseAmountValue(raw);
    feedbackEl.className = "small mt-1";
    feedbackEl.innerHTML = "";

    if (!raw.trim()) {
      feedbackEl.textContent = "";
      return;
    }
    if (!parsed.ok) {
      if (parsed.code === "decimals") {
        feedbackEl.className += " text-danger";
        feedbackEl.textContent = "金额最多保留两位小数。";
      } else if (parsed.code === "nonpositive") {
        feedbackEl.className += " text-danger";
        feedbackEl.textContent = "金额不能为 0 或负数。";
      } else {
        feedbackEl.className += " text-danger";
        feedbackEl.textContent = "请输入有效数字（仅 0-9 与小数点）。";
      }
      return;
    }
    var vr = validateAgainstProduct(parsed.value, meta);
    if (!vr.ok) {
      feedbackEl.className += " text-danger";
      feedbackEl.textContent = vr.msg;
      return;
    }
    feedbackEl.className += " text-success";
    feedbackEl.innerHTML = "&#10003; 金额在允许范围内";
  }

  function bindForm(form) {
    var selectEl = form.querySelector('select[name="card_product"]');
    var inputEl = form.querySelector('input[name="amount"]');
    if (!inputEl || inputEl.type === "hidden") return;

    var hintId = inputEl.getAttribute("data-amount-range-hint-id") || "amount-range-hint";
    var fbId = inputEl.getAttribute("data-amount-feedback-id") || "amount-live-feedback";
    var hintEl = document.getElementById(hintId);
    var feedbackEl = document.getElementById(fbId);

    function refresh() {
      updateRangeHint(selectEl, hintEl);
      updateLiveFeedback(inputEl, selectEl, feedbackEl);
    }

    inputEl.addEventListener("beforeinput", function (e) {
      if (e.data == null) return;
      for (var i = 0; i < e.data.length; i++) {
        var ch = e.data[i];
        if ((ch < "0" || ch > "9") && ch !== ".") {
          e.preventDefault();
          return;
        }
      }
    });

    inputEl.addEventListener("input", function () {
      var cur = inputEl.value;
      var next = sanitizeAmountString(cur);
      if (next !== cur) inputEl.value = next;
      refresh();
    });

    inputEl.addEventListener("paste", function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData("text") || "";
      var next = sanitizeAmountString(text);
      inputEl.value = next;
      refresh();
    });

    if (selectEl) {
      selectEl.addEventListener("change", refresh);
    }
    refresh();

    form.addEventListener(
      "submit",
      function (e) {
        var raw = (inputEl.value || "").trim();
        if (!raw) {
          e.preventDefault();
          e.stopImmediatePropagation();
          alert("申请金额不能为空。");
          return;
        }
        var t = raw.startsWith(".") ? "0" + raw : raw;
        if (!/^\d+(\.\d{0,2})?$/.test(t)) {
          if (t.indexOf(".") >= 0 && t.split(".")[1].length > 2) {
            e.preventDefault();
            e.stopImmediatePropagation();
            alert("金额最多保留两位小数。");
            return;
          }
          e.preventDefault();
          e.stopImmediatePropagation();
          alert("请输入有效数字。");
          return;
        }
        var v = parseFloat(t);
        if (!isFinite(v) || v <= 0) {
          e.preventDefault();
          e.stopImmediatePropagation();
          alert("金额不能为 0 或负数。");
          return;
        }
        var meta = getSelectedProductMeta(selectEl);
        var vr = validateAgainstProduct(v, meta);
        if (!vr.ok) {
          e.preventDefault();
          e.stopImmediatePropagation();
          alert(vr.msg);
        }
      },
      true,
    );
  }

  document.querySelectorAll("form").forEach(function (form) {
    if (form.method && form.method.toLowerCase() !== "post") return;
    if (!form.querySelector('input[name="amount"]')) return;
    bindForm(form);
  });
})();
