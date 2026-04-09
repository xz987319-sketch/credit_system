import re

template = open('apply/templates/includes/_dynamic_fields.html', encoding='utf-8').read()

# Find all if/endif between textarea and number
start = template.find("{% if field.field_type == 'textarea' %}")
end = template.find("{% if field.field_type == 'number' %}")
segment = template[start:end]

print('Segment between textarea and number:')
print('Length:', len(segment))
print()

# Find all tags in this segment
tags = [(m.start(), m.group()) for m in re.finditer(r'{%\s*(if|elif|else|endif)[^}]*%}', segment)]
level = 0
for off, tag in tags:
    is_if = '{% if' in tag or '{% elif' in tag
    is_endif = '{% endif %}' in tag
    if is_if:
        level += 1
    elif is_endif:
        level -= 1
    print(f'L{level:2d} off={off:4d}: {tag[:60]}')
