template = open('apply/templates/includes/_dynamic_fields.html', encoding='utf-8').read()
import re

tags = [(m.start(), m.group()) for m in re.finditer(r'{%\s*(if|elif|else|endif)[^}]*%}', template)]
ftags = [(p,t) for p,t in tags if 'field_type' in t or 'validation_rule' in t]
print(f'Found {len(ftags)} field-related template tags:')
for p,t in ftags:
    print(f'  pos={p}: {t[:80]}')

print()

# Check nesting - trace level changes
open_ifs = 0
changes = []
for pos, tag in tags:
    if '{% if' in tag or '{% elif' in tag:
        open_ifs += 1
    elif '{% endif %}' in tag:
        open_ifs -= 1
    changes.append((open_ifs, pos, tag[:70]))

# Show field-related and level changes
for level, pos, tag in changes:
    if 'field_type' in tag or 'validation_rule' in tag or ('{% endif %}' in tag and level <= 2):
        print(f'  level={level} pos={pos}: {tag}')
