# -*- coding: utf-8 -*-
import re

# 先读取文件
with open('apply/templates/multi_step_form.html', 'rb') as f:
    raw = f.read()

print(f"File size: {len(raw)} bytes")
print(f"First 500 bytes: {raw[:500]}")

# 尝试找到需要删除的内容
# 在文件中搜索 "提取纯汉字数量"
idx = raw.find('提取纯汉字数量'.encode('utf-8'))
if idx != -1:
    print(f"Found at index {idx}")
    print(f"Context: {raw[idx-50:idx+200]}")
else:
    print("Not found with utf-8")
    # 尝试其他编码
    for enc in ['gbk', 'gb2312', 'latin-1']:
        try:
            idx = raw.find('提取纯汉字数量'.encode(enc))
            print(f"Found with {enc} at index {idx}")
        except:
            pass
