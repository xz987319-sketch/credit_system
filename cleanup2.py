# -*- coding: utf-8 -*-
import re

# 先读取文件
with open('apply/templates/multi_step_form.html', 'rb') as f:
    raw = f.read()

# 需要删除的内容（UTF-8 编码）
# "提取纯汉字数量（排除间隔符·）" -> "\xe6\x8f\x90\xe5\x8f\x96\xe7\xba\xaf\xe6\xb1\x89\xe5\xad\x97\xe6\x95\xb0\xe9\x87\x8f\xef\xbc\x88\xe6\x8e\x92\xe9\x99\xa4\xe9\x97\xb4\xe9\x9a\x94\xe7\xac\xa6\xc2\xb7\xef\xbc\x89"
# "var chineseChars = value.replace(/·/g, '')" -> "var chineseChars = value.replace(/\xc2\xb7/g, '')"
# "var chineseCount = chineseChars ? chineseChars.length : 0;" -> "var chineseCount = chineseChars ? chineseChars.length : 0;"

old_bytes = (
    b"// \xe6\x8f\x90\xe5\x8f\x96\xe7\xba\xaf\xe6\xb1\x89\xe5\xad\x97\xe6\x95\xb0\xe9\x87\x8f\xef\xbc\x88\xe6\x8e\x92\xe9\x99\xa4\xe9\x97\xb4\xe9\x9a\x94\xe7\xac\xa6\xc2\xb7\xef\xbc\x89\n"
    b"        var chineseChars = value.replace(/\xc2\xb7/g, '').match(/[\\\\u4e00-\\\\u9fa5]/g);\n"
    b"        var chineseCount = chineseChars ? chineseChars.length : 0;\n"
    b"        \n"
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
    print('Pattern not found')
    print('Looking for similar patterns...')
    # 尝试找到类似的内容
    idx = raw.find(b'\xe6\x8f\x90\xe5\x8f\x96\xe7\xba\xaf')
    if idx != -1:
        print(f'Found start at {idx}')
        print(f'Context: {raw[idx:idx+300]}')
