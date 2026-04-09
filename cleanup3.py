# -*- coding: utf-8 -*-

# 先读取文件
with open('apply/templates/multi_step_form.html', 'rb') as f:
    raw = f.read()

# 需要删除的内容（UTF-8 编码，使用 CRLF）
old_bytes = (
    b"// \xe6\x8f\x90\xe5\x8f\x96\xe7\xba\xaf\xe6\xb1\x89\xe5\xad\x97\xe6\x95\xb0\xe9\x87\x8f\xef\xbc\x88\xe6\x8e\x92\xe9\x99\xa4\xe9\x97\xb4\xe9\x9a\x94\xe7\xac\xa6\xc2\xb7\xef\xbc\x89\r\n"
    b"        var chineseChars = value.replace(/\xc2\xb7/g, '').match(/[\\\\u4e00-\\\\u9fa5]/g);\r\n"
    b"        var chineseCount = chineseChars ? chineseChars.length : 0;\r\n"
    b"        \r\n"
    b"        // \xe9\x9d\x9e\xe7\xa9\xba\xe6\xa0\x87\xe5\x87\x96"
)

new_bytes = (
    b"        // \xe9\x9d\x9e\xe7\xa9\xba\xe6\xa0\x87\xe5\x87\x96"
)

if old_bytes in raw:
    new_content = raw.replace(old_bytes, new_bytes)
    with open('apply/templates/multi_step_form.html', 'wb') as f:
        f.write(new_content)
    print('Done! Removed redundant code')
else:
    print('Pattern not found exactly, trying flexible match...')
    # 灵活匹配
    start = raw.find(b'\xe6\x8f\x90\xe5\x8f\x96\xe7\xba\xaf')
    if start != -1:
        end = raw.find(b'// \xe9\x9d\x9e\xe7\xa9\xba', start)
        if end != -1:
            # 包括前面的 }
            block_start = raw.rfind(b'}', 0, start)
            to_remove = raw[block_start:end]
            print(f'Found block to remove, length: {len(to_remove)}')
            print(f'Content: {to_remove}')
            new_content = raw.replace(to_remove, b'}')
            with open('apply/templates/multi_step_form.html', 'wb') as f:
                f.write(new_content)
            print('Done!')
