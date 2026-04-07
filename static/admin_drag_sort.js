/**
 * 表单页面拖拽排序功能 - 改进版
 */
(function() {
    'use strict';

    let draggedItem = null;
    let draggedHandle = null;

    function init() {
        console.log('[DragSort] Initializing...');

        // 等待表格加载
        setTimeout(setupDragSort, 800);
    }

    function setupDragSort() {
        const handles = document.querySelectorAll('.drag-handle');
        console.log('[DragSort] Found', handles.length, 'drag handles');

        if (handles.length === 0) {
            // 重试
            setTimeout(setupDragSort, 500);
            return;
        }

        handles.forEach(handle => {
            // 样式
            handle.style.cssText = 'cursor: grab; display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; color: #999; background: #f5f5f5; border-radius: 4px; user-select: none;';
            handle.querySelector('svg').style.cssText = 'display: block;';

            // 鼠标按下开始拖拽
            handle.addEventListener('mousedown', function(e) {
                e.preventDefault();
                e.stopPropagation();

                draggedHandle = this;
                const row = this.closest('tr');
                if (!row) return;

                draggedItem = row;
                row.style.opacity = '0.6';
                row.style.background = '#e3f2fd';

                console.log('[DragSort] Started dragging row');
            });
        });

        // 全局鼠标移动
        document.addEventListener('mousemove', function(e) {
            if (!draggedItem) return;

            const rows = Array.from(document.querySelectorAll('table tbody tr'));
            let targetRow = null;

            for (const row of rows) {
                if (row === draggedItem) continue;

                const rect = row.getBoundingClientRect();
                if (e.clientY >= rect.top && e.clientY <= rect.bottom) {
                    targetRow = row;
                    break;
                }
            }

            if (targetRow) {
                const rect = targetRow.getBoundingClientRect();
                const midY = rect.top + rect.height / 2;

                if (e.clientY < midY) {
                    // 插入到目标行之前
                    targetRow.parentNode.insertBefore(draggedItem, targetRow);
                } else {
                    // 插入到目标行之后
                    targetRow.parentNode.insertBefore(draggedItem, targetRow.nextSibling);
                }
            }
        });

        // 全局鼠标释放
        document.addEventListener('mouseup', function(e) {
            if (!draggedItem) return;

            console.log('[DragSort] Dropped');

            draggedItem.style.opacity = '';
            draggedItem.style.background = '';

            // 保存新顺序
            saveOrder();

            draggedItem = null;
            draggedHandle = null;
        });

        console.log('[DragSort] Setup complete');
    }

    function saveOrder() {
        const rows = document.querySelectorAll('table tbody tr');
        const orders = [];

        rows.forEach((row, index) => {
            const handle = row.querySelector('.drag-handle');
            if (handle && handle.dataset.id) {
                orders.push({ id: parseInt(handle.dataset.id), order: index });
            }
        });

        console.log('[DragSort] Saving order:', orders);

        if (orders.length === 0) return;

        fetch('/admin/apply/formpage/drag-sort/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ orders: orders })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                console.log('[DragSort] Saved successfully');
                updateOrderDisplay(orders);
            } else {
                console.error('[DragSort] Save failed:', data.error);
                alert('保存失败: ' + data.error);
            }
        })
        .catch(err => {
            console.error('[DragSort] Error:', err);
        });
    }

    function updateOrderDisplay(orders) {
        orders.forEach((item, idx) => {
            const handle = document.querySelector(`.drag-handle[data-id="${item.id}"]`);
            if (handle) {
                const row = handle.closest('tr');
                if (row) {
                    // 更新第一列的显示
                    const firstTd = row.querySelector('td');
                    if (firstTd) {
                        firstTd.textContent = item.order;
                    }
                }
            }
        });
    }

    function getCsrfToken() {
        // 多种方式获取 CSRF token
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (input) return input.value;

        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;

        const match = document.cookie.match(/csrftoken=([^;]+)/);
        if (match) return match[1];

        return '';
    }

    // 启动
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
