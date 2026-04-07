/**
 * 用户详情页双栏选择器（组/权限/可见窗口）全中文翻译
 *
 * Django SelectFilter2.js 硬编码了大量英文 gettext() 调用，
 * 本脚本在 DOM 渲染完成后批量替换为中文，覆盖所有已知文本节点。
 *
 * SelectFilter2.js 关键文本索引（行号）：
 *   45: 'Available %s'         → 可用窗口
 *   49: 'Choose %s by selecting them...'  → 左栏说明
 *   61: 'Type into this box to filter down available %s.'  → 左栏搜索提示
 *   66: 'Filter'                → 搜索
 *   73: 'Choose all %s'         → 全部选择
 *   85: 'Choose selected %s'   → 选择（箭头按钮）
 *   93: 'Remove selected %s'   → 移除（箭头按钮）
 *  105: 'Chosen %s'            → 已选窗口
 *  109: 'Remove %s by selecting...' → 右栏说明
 *  121: 'Type into this box to filter down selected %s.'  → 右栏搜索提示
 *  126: 'Filter'                → 搜索
 *  142: '(click to clear)'      → 点击清除
 *  146: 'Remove all %s'          → 清除全部
 *  239: '%s selected option(s) not visible' → 个选中项不可见
 */
(function () {
    'use strict';

    function translateSelectorText() {
        var i, el, label;

        /* ── 左栏标题：Available %s ─────────────────────────── */
        document.querySelectorAll('.selector-available-title label').forEach(function (el) {
            el.textContent = el.textContent.replace(/^Available /, '可用 ');
        });

        /* ── 左栏帮助说明：Choose %s by selecting them... ──── */
        document.querySelectorAll('.selector-available-title .helptext').forEach(function (el) {
            if (el.textContent.indexOf('Choose') !== -1) {
                el.textContent = '从左侧列表中选择后，点击移动箭头移至右侧。';
            }
        });

        /* ── 左栏搜索框 placeholder：Filter → 搜索 ─────────── */
        document.querySelectorAll('.selector-available .selector-filter input[type="text"]').forEach(function (el) {
            if (el.placeholder === 'Filter') el.placeholder = '搜索…';
        });

        /* ── 左栏搜索框 aria-label ─────────────────────────── */
        document.querySelectorAll('.selector-available .selector-filter label[aria-label]').forEach(function (el) {
            var a = el.getAttribute('aria-label');
            if (a && a.indexOf('Type into') !== -1) {
                el.setAttribute('aria-label', '输入关键字搜索可用列表');
            }
        });

        /* ── 全部选择按钮：Choose all %s → 全部选择 ─────────── */
        document.querySelectorAll('.selector-chooseall').forEach(function (el) {
            el.textContent = el.textContent.replace('Choose all', '全部选择');
        });

        /* ── 移动箭头按钮：选择 ──────────────────────────────── */
        document.querySelectorAll('.selector-add').forEach(function (el) {
            el.textContent = el.textContent.replace(/^Choose selected /, '选择');
        });

        /* ── 移动箭头按钮：移除 ──────────────────────────────── */
        document.querySelectorAll('.selector-remove').forEach(function (el) {
            el.textContent = el.textContent.replace(/^Remove selected /, '移除');
        });

        /* ── 右栏标题：Chosen %s ───────────────────────────── */
        document.querySelectorAll('.selector-chosen-title label').forEach(function (el) {
            el.textContent = el.textContent.replace(/^Chosen /, '已选 ');
        });

        /* ── 右栏帮助说明：Remove %s by selecting... ────────── */
        document.querySelectorAll('.selector-chosen-title .helptext').forEach(function (el) {
            if (el.textContent.indexOf('Remove') !== -1) {
                el.textContent = '从右侧列表中选择后，点击移动箭头移回左侧。';
            }
        });

        /* ── 右栏搜索框 placeholder ─────────────────────────── */
        document.querySelectorAll('.selector-chosen .selector-filter input[type="text"]').forEach(function (el) {
            if (el.placeholder === 'Filter') el.placeholder = '搜索…';
        });

        /* ── 右栏搜索框 aria-label ─────────────────────────── */
        document.querySelectorAll('.selector-chosen .selector-filter label[aria-label]').forEach(function (el) {
            var a = el.getAttribute('aria-label');
            if (a && a.indexOf('Type into') !== -1) {
                el.setAttribute('aria-label', '输入关键字搜索已选列表');
            }
        });

        /* ── 底部点击清除提示：(click to clear) ────────────── */
        document.querySelectorAll('.list-footer-display__clear').forEach(function (el) {
            el.textContent = el.textContent.replace('(click to clear)', '（点击清除）');
        });

        /* ── 全部清除按钮：Remove all %s → 清除全部 ──────────── */
        document.querySelectorAll('.selector-clearall').forEach(function (el) {
            el.textContent = el.textContent.replace('Remove all', '清除全部');
        });
    }

    /* ── 执行时机：DOMContentLoaded 后等待 SelectFilter2.js 渲染完成 ── */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(translateSelectorText, 500); });
    } else {
        setTimeout(translateSelectorText, 500);
    }

    /* ── 监听 HTMX 表单刷新（Unfold 使用 HTMX 更新表单区域）── */
    document.addEventListener('htmx:afterSwap', function () {
        setTimeout(translateSelectorText, 300);
    });
})();
