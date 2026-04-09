import re

template = open('apply/templates/includes/_dynamic_fields.html', encoding='utf-8').read()

# Extract all template if/endif tags
tags = [(m.start(), m.group()) for m in re.finditer(r'{%\s*(if|elif|else|endif)[^}]*%}', template)]

# Find the editable section (around position 4966+)
editable_tags = [(p, t) for p, t in tags if 4966 <= p < 23000]

print(f'Total if/endif tags in editable section: {len(editable_tags)}')
print()

# Trace nesting level
level = 0
for pos, tag in editable_tags:
    is_if = '{% if' in tag or '{% elif' in tag
    is_endif = '{% endif %}' in tag
    if is_if:
        level += 1
    elif is_endif:
        level -= 1
    # Show field-related tags or level changes
    snippet = tag[:70]
    print(f'L{level:2d} pos={pos}: {snippet}')
