# -*- coding: utf-8 -*-
import re

with open('apply/templates/multi_step_form.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 删除包含 "提取纯汉字数量" 的注释行和接下来的两行
# 注意：这里用原始字符串避免转义问题
pattern = r'        // 提取纯汉字数量（排除间隔符·）\s+var chineseChars = value\.replace\(/·/g, \'\'\)\.match\(/[\u4e00-\u9fa5]\/g\);\s+var chineseCount = chineseChars \? chineseChars\.length : 0;\s+'
replacement = ''
new_content = re.sub(pattern, replacement, content)

if new_content != content:
    with open('apply/templates/multi_step_form.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Done - removed redundant code')
else:
    print('Pattern not found, trying simpler approach')
    # 简单替换
    old = "        // 提取纯汉字数量（排除间隔符·）\n        var chineseChars = value.replace(/·/g, '').match(/[\u4e00-\u9fa5]/g);\n        var chineseCount = chineseChars ? chineseChars.length : 0;\n        \n        "
    new = "        "
    new_content = content.replace(old, new)
    if new_content != content:
        with open('apply/templates/multi_step_form.html', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print('Done - simple replace')
    else:
        print('Simple replace also failed')
