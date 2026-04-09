import re
t = open('apply/templates/includes/_dynamic_fields.html', encoding='utf-8').read()
tokens = [(m.start(), m.group()) for m in re.finditer(r'{%\s*(if|elif|else|endif)[^}]*%}', t)]
stack = []
errors = []
for pos, tok in tokens:
    line = t[:pos].count('\n') + 1
    if '{% if' in tok or '{% elif' in tok:
        stack.append((tok[:60], line))
    elif '{% endif %}' in tok:
        if stack:
            stack.pop()
        else:
            errors.append(f'Line {line}: endif without if')
if stack:
    for item, line in stack:
        errors.append(f'Line {line}: unclosed if: {item}')
if errors:
    print('Nesting errors:')
    for e in errors:
        print(e)
else:
    print('OK: if/endif 配对正确')
