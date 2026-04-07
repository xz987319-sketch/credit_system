"""
自定义 Widget 模块。

包含：
  - ColorSelectWidget：带色块预览的品牌色下拉选择器。
  - CardProductLimitsSelect：给卡种下拉 option 加 data-credit-min/max 属性，供前端 JS 读取额度区间。
  - MenuVisibilityWidget / MenuVisibilityField：双栏菜单控制选择器，用于后台用户编辑页。
  - TranslatedFilteredSelectMultiple：用户权限选择器，将 "Can add/change/delete/view X"
    等英文权限名翻译为中文，配合 filter_horizontal 使用。
"""
import json
import re

from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.html import format_html, mark_safe

from apply.models.user import MENU_ITEMS  # 导入菜单定义列表


# ════════════════════════════════════════════════════════════════════════════
# ColorSelectWidget — 带色块预览的品牌色下拉选择器
# ════════════════════════════════════════════════════════════════════════════

class ColorSelectWidget(forms.Select):
    """
    继承自 forms.Select，在每个 <option> 左侧渲染一个对应颜色的色块。

    实现方式：
      - 覆盖 render() 输出自定义 HTML，用 <select> 包裹 <option>。
      - 通过 CSS + JS 在选中后实时更新左侧预览色块。
    """

    def __init__(self, attrs=None, choices=()):
        # 显式接收 choices，确保父类正确处理
        super().__init__(attrs=attrs)
        self.choices = choices

    def render(self, name, value, attrs=None, renderer=None):
        # 修复：优先用 BRAND_COLOR_CHOICES 构建 options（解决 choices 未传递时的显示问题）
        from apply.models.bank import BRAND_COLOR_CHOICES
        choices_list = list(self.choices) if self.choices else BRAND_COLOR_CHOICES

        # 构建 option HTML，每个选项带 data-color 属性
        options_html = '<option value="">---------</option>'
        for hex_val, label in choices_list:
            if not hex_val:
                continue
            selected = 'selected' if str(value).strip() == str(hex_val).strip() else ''
            options_html += (
                f'<option value="{hex_val}" data-color="{hex_val}" {selected}>'
                f'{label} ({hex_val})'
                f'</option>'
            )

        # 当前选中色，用于初始预览色块
        current_color = (value or '#3182ce').strip()
        widget_id = attrs.get('id', f'id_{name}') if attrs else f'id_{name}'

        html = f"""
<div class="color-select-wrapper" style="display:inline-flex;align-items:center;gap:10px;max-width:320px;">
  <span id="{widget_id}_preview"
        style="display:inline-block;width:28px;height:28px;border-radius:6px;
               background:{current_color};border:1px solid #ccc;flex-shrink:0;
               box-shadow:0 1px 3px rgba(0,0,0,.2);transition:background .2s;"></span>
  <select name="{name}" id="{widget_id}"
          style="flex:1;min-width:180px;"
          onchange="
            var c=this.options[this.selectedIndex].getAttribute('data-color');
            if(c){{document.getElementById('{widget_id}_preview').style.background=c;}}
          ">
    {options_html}
  </select>
</div>
"""
        return mark_safe(html)


class MenuVisibilityWidget(forms.Widget):
    """
    双栏菜单可见性控制 Widget。

    渲染一个左右双栏选择界面：
      - 左栏：可用窗口（所有 MENU_ITEMS，按分组展示）
      - 右栏：已选中的窗口（已在 visible_menus 中的项）
      - 中间：← → 箭头按钮，移动选中项
    保存时，右栏的 key 列表作为 JSON 写入 visible_menus 字段。
    """

    template_name = None  # 不使用 Django 模板，直接 render()

    class Media:
        css = {"all": []}
        js = []

    def render(self, name, value, attrs=None, renderer=None):
        # value 是当前已选中的 key 列表（JSON 字符串或 list）
        if isinstance(value, str):
            try:
                selected_keys = json.loads(value) if value else []
            except (json.JSONDecodeError, TypeError):
                selected_keys = []
        elif isinstance(value, list):
            selected_keys = value
        else:
            selected_keys = []

        widget_id = attrs.get("id", f"id_{name}") if attrs else f"id_{name}"

        # 按分组整理菜单项
        groups: dict[str, list] = {}
        all_keys_ordered = []
        for key, group, label in MENU_ITEMS:
            groups.setdefault(group, []).append((key, label))
            all_keys_ordered.append(key)

        # 构建左栏 HTML（未选中的项）
        left_items_html = ""
        for group, items in groups.items():
            left_items_html += f'<optgroup label="{group}">'
            for key, label in items:
                if key not in selected_keys:
                    left_items_html += f'<option value="{key}">{label}</option>'
            left_items_html += "</optgroup>"

        # 构建右栏 HTML（已选中的项，保持顺序）
        right_items_html = ""
        # 先按 MENU_ITEMS 顺序排右栏，再加上不在定义里的（容错）
        for key, group, label in MENU_ITEMS:
            if key in selected_keys:
                right_items_html += f'<option value="{key}">[{group}] {label}</option>'

        # 隐藏的 input，存储最终 JSON 值
        hidden_input = format_html(
            '<input type="hidden" name="{}" id="{}_hidden" value="{}">',
            name,
            widget_id,
            json.dumps(selected_keys, ensure_ascii=False),
        )

        html = f"""
        {hidden_input}
        <div id="{widget_id}_container" style="display:flex;align-items:flex-start;gap:10px;margin-top:8px;">
            <!-- 左栏：可用窗口 -->
            <div style="flex:1;">
                <div style="font-size:12px;color:#666;margin-bottom:4px;">可用窗口</div>
                <select id="{widget_id}_left" multiple size="12"
                    style="width:100%;border:1px solid #d1d5db;border-radius:6px;
                           padding:4px;font-size:13px;background:#fff;min-height:200px;">
                    {left_items_html}
                </select>
                <div style="margin-top:6px;">
                    <button type="button"
                        onclick="menuWidgetSelectAll('{widget_id}')"
                        style="font-size:12px;padding:2px 10px;border:1px solid #d1d5db;
                               border-radius:4px;cursor:pointer;background:#f9fafb;">
                        全部选中 &rarr;
                    </button>
                </div>
            </div>

            <!-- 中间按钮 -->
            <div style="display:flex;flex-direction:column;justify-content:center;
                        gap:8px;padding-top:28px;">
                <button type="button"
                    onclick="menuWidgetMoveRight('{widget_id}')"
                    title="将选中项移至右侧"
                    style="padding:6px 10px;border:1px solid #6366f1;border-radius:6px;
                           background:#6366f1;color:#fff;cursor:pointer;font-size:14px;">
                    &rarr;
                </button>
                <button type="button"
                    onclick="menuWidgetMoveLeft('{widget_id}')"
                    title="将选中项移回左侧"
                    style="padding:6px 10px;border:1px solid #6366f1;border-radius:6px;
                           background:#6366f1;color:#fff;cursor:pointer;font-size:14px;">
                    &larr;
                </button>
            </div>

            <!-- 右栏：已选中的窗口 -->
            <div style="flex:1;">
                <div style="font-size:12px;color:#666;margin-bottom:4px;">已选中的窗口（保存后生效）</div>
                <select id="{widget_id}_right" multiple size="12"
                    style="width:100%;border:1px solid #6366f1;border-radius:6px;
                           padding:4px;font-size:13px;background:#fff;min-height:200px;">
                    {right_items_html}
                </select>
                <div style="margin-top:6px;display:flex;gap:6px;">
                    <button type="button"
                        onclick="menuWidgetClearAll('{widget_id}')"
                        style="font-size:12px;padding:2px 10px;border:1px solid #d1d5db;
                               border-radius:4px;cursor:pointer;background:#f9fafb;">
                        &larr; 全部移回
                    </button>
                </div>
            </div>
        </div>
        <div style="margin-top:6px;font-size:12px;color:#9ca3af;">
            提示：右侧为空时表示该用户可见所有窗口；超级管理员不受此限制，始终显示全部。
        </div>

        <!-- 所有菜单 key 的有序列表，供 JS 用于重建 optgroup -->
        <script>
        (function() {{
            // 菜单定义：[key, group, label]
            var MENU_DEFS_{widget_id} = {json.dumps(
                [[k, g, l] for k, g, l in MENU_ITEMS],
                ensure_ascii=False
            )};

            // 同步隐藏 input 的值
            function syncHidden(wid) {{
                var rightSel = document.getElementById(wid + '_right');
                var keys = [];
                for (var i = 0; i < rightSel.options.length; i++) {{
                    keys.push(rightSel.options[i].value);
                }}
                document.getElementById(wid + '_hidden').value = JSON.stringify(keys);
            }}

            // 将左栏选中项移至右栏
            window.menuWidgetMoveRight = function(wid) {{
                var leftSel = document.getElementById(wid + '_left');
                var rightSel = document.getElementById(wid + '_right');
                var toMove = [];
                for (var i = leftSel.options.length - 1; i >= 0; i--) {{
                    if (leftSel.options[i].selected) {{
                        toMove.unshift(leftSel.options[i].value);
                        leftSel.remove(i);
                    }}
                }}
                // 按 MENU_DEFS 顺序重建右栏
                var rightKeys = [];
                for (var j = 0; j < rightSel.options.length; j++) {{
                    rightKeys.push(rightSel.options[j].value);
                }}
                toMove.forEach(function(k) {{ if (rightKeys.indexOf(k) === -1) rightKeys.push(k); }});
                rebuildRight(wid, rightKeys);
                syncHidden(wid);
            }};

            // 将右栏选中项移回左栏
            window.menuWidgetMoveLeft = function(wid) {{
                var rightSel = document.getElementById(wid + '_right');
                var toRemove = [];
                for (var i = rightSel.options.length - 1; i >= 0; i--) {{
                    if (rightSel.options[i].selected) {{
                        toRemove.push(rightSel.options[i].value);
                        rightSel.remove(i);
                    }}
                }}
                rebuildLeft(wid);
                syncHidden(wid);
            }};

            // 全部选中（移至右栏）
            window.menuWidgetSelectAll = function(wid) {{
                var leftSel = document.getElementById(wid + '_left');
                for (var i = 0; i < leftSel.options.length; i++) {{
                    leftSel.options[i].selected = true;
                }}
                menuWidgetMoveRight(wid);
            }};

            // 全部移回左栏
            window.menuWidgetClearAll = function(wid) {{
                document.getElementById(wid + '_right').innerHTML = '';
                rebuildLeft(wid);
                syncHidden(wid);
            }};

            // 重建右栏（按 MENU_DEFS 顺序）
            function rebuildRight(wid, keys) {{
                var rightSel = document.getElementById(wid + '_right');
                rightSel.innerHTML = '';
                var defs = MENU_DEFS_{widget_id};
                defs.forEach(function(def) {{
                    if (keys.indexOf(def[0]) !== -1) {{
                        var opt = document.createElement('option');
                        opt.value = def[0];
                        opt.textContent = '[' + def[1] + '] ' + def[2];
                        rightSel.appendChild(opt);
                    }}
                }});
            }}

            // 重建左栏（排除右栏已有的）
            function rebuildLeft(wid) {{
                var rightSel = document.getElementById(wid + '_right');
                var rightKeys = [];
                for (var i = 0; i < rightSel.options.length; i++) {{
                    rightKeys.push(rightSel.options[i].value);
                }}
                var leftSel = document.getElementById(wid + '_left');
                leftSel.innerHTML = '';
                var defs = MENU_DEFS_{widget_id};
                var groups = {{}};
                defs.forEach(function(def) {{
                    if (rightKeys.indexOf(def[0]) === -1) {{
                        if (!groups[def[1]]) groups[def[1]] = [];
                        groups[def[1]].push(def);
                    }}
                }});
                Object.keys(groups).forEach(function(grp) {{
                    var og = document.createElement('optgroup');
                    og.label = grp;
                    groups[grp].forEach(function(def) {{
                        var opt = document.createElement('option');
                        opt.value = def[0];
                        opt.textContent = def[2];
                        og.appendChild(opt);
                    }});
                    leftSel.appendChild(og);
                }});
            }}
        }})();
        </script>
        """
        return html

    def value_from_datadict(self, data, files, name):
        """从表单提交数据中读取隐藏 input 的 JSON 值。"""
        raw = data.get(name, "[]")
        try:
            result = json.loads(raw)
            if not isinstance(result, list):
                result = []
        except (json.JSONDecodeError, TypeError):
            result = []
        return result


class MenuVisibilityField(forms.Field):
    """对应 MenuVisibilityWidget 的表单字段，处理 JSON list 的序列化/反序列化。"""

    widget = MenuVisibilityWidget

    def prepare_value(self, value):
        if isinstance(value, list):
            return json.dumps(value, ensure_ascii=False)
        return value or "[]"

    def to_python(self, value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                result = json.loads(value)
                return result if isinstance(result, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        return sorted(initial) != sorted(data)


# ════════════════════════════════════════════════════════════════════════════
# CardProductLimitsSelect — H5 卡种下拉带额度区间 data 属性
# ════════════════════════════════════════════════════════════════════════════

class CardProductLimitsSelect(forms.Select):
    """
    卡种下拉控件，在每个 <option> 上注入 data-credit-min / data-credit-max 属性。

    前端 apply_amount_input.js 读取这两个属性，在用户选择卡种后
    实时显示可申请金额区间，并在提交时做客户端预校验。
    """

    def optgroups(self, name, value, attrs=None):
        """覆盖 optgroups，为每个选项追加额度区间 data 属性。"""
        groups = super().optgroups(name, value, attrs)
        # groups 结构：[(group_name, subgroup, index), ...]
        # subgroup 是 option dict 列表
        for group_name, subgroup, index in groups:
            for option in subgroup:
                obj = self._get_card_product(option.get("value"))
                if obj is not None:
                    option.setdefault("attrs", {})
                    option["attrs"]["data-credit-min"] = str(obj.credit_limit_min)
                    option["attrs"]["data-credit-max"] = str(obj.credit_limit_max)
        return groups

    def _get_card_product(self, pk_value):
        """根据 option value（卡产品主键）获取对应的 CardProduct 实例。"""
        if not pk_value:
            return None
        try:
            from apply.models import CardProduct  # 延迟导入避免循环
            return CardProduct.objects.get(pk=int(pk_value))
        except (CardProduct.DoesNotExist, ValueError, TypeError):
            return None


# ════════════════════════════════════════════════════════════════════════════
# TranslatedFilteredSelectMultiple — 权限名中文化双栏选择器
# ════════════════════════════════════════════════════════════════════════════

# 动作动词：英文 → 中文（支持多种写法的变体）
_PERM_VERB_MAP = {
    "can add":    "可添加",
    "can change": "可修改",
    "can delete": "可删除",
    "can view":   "可查看",
}

# 常见模型名：英文小写 → 中文
_PERM_MODEL_MAP = {
    "log entry":          "日志",
    "group":              "用户组",
    "user":               "用户",
    "bank":               "银行",
    "card product":       "卡产品",
    "credit application": "进件申请",
    "menu item":          "菜单项",
    "apply":              "申请",
    "application":        "申请",
    "logentry":           "日志",
}


def _translate_permission_name(name: str) -> str:
    """
    将 Django 权限名称（如 'Can add log entry'）翻译为中文（如 '可添加日志'）。
    使用正则处理动词 + 模型名的各种大小写组合。
    """
    if not name:
        return name

    text = name.lower()
    result = name  # 默认保留原文

    # 1. 匹配 "Can add/change/delete/view X" 模式
    # 常见的动词形式：can add, can change, can delete, can view
    for eng_verb, chn_verb in _PERM_VERB_MAP.items():
        if eng_verb in text:
            # 提取动词后面的模型名部分
            pos = text.index(eng_verb)
            model_part = text[pos + len(eng_verb):].strip()
            # 去掉可能的前置词 "the"
            model_part = re.sub(r"^the\s+", "", model_part)

            # 翻译模型名
            model_translated = model_part
            for eng_model, chn_model in _PERM_MODEL_MAP.items():
                if model_part == eng_model or model_part.startswith(eng_model + " "):
                    model_translated = chn_model + (" " + model_part[len(eng_model):].strip() if len(model_part) > len(eng_model) else "")
                    break

            # 如果没有匹配到已知的模型名，尝试用正则去掉后缀保留原样
            # 例如 "Can add bank" → "可添加银行" (bank 会被 _PERM_MODEL_MAP 匹配)
            # 如果完全没匹配，使用原文但翻译动词
            if model_translated == model_part and model_part:
                # 尝试把每个单词首字母大写作为原文显示
                pass  # 保留原文

            # 组合中文结果
            if model_translated != model_part or model_part:
                result = f"{chn_verb}{model_translated}"
            else:
                result = f"{chn_verb}（{name}）"
            break

    return result


class TranslatedFilteredSelectMultiple(FilteredSelectMultiple):
    """
    继承自 Django 的 FilteredSelectMultiple，在渲染每个权限选项时
    将英文权限名（如 'Can add log entry'）翻译为中文（如 '可添加日志'）。

    使用方式（在 UserAdmin 中）：
        def formfield_for_dbptr(self, db_field, request, **kwargs):
            if db_field.name == "user_permissions":
                kwargs.setdefault("widget", TranslatedFilteredSelectMultiple("权限", False))
            return super().formfield_for_dbptr(db_field, request, **kwargs)
    """

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        """覆写 create_option：将权限 label 翻译为中文。"""
        translated_label = _translate_permission_name(str(label))
        return super().create_option(
            name, value, translated_label, selected, index, subindex=subindex, attrs=attrs
        )
