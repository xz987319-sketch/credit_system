t = open('apply/templates/includes/_dynamic_fields.html', encoding='utf-8').read()
idx = t.find("{% elif field.field_type == 'select' %}")
print(f'Found at: {idx}')
if idx >= 0:
    print('Context:')
    print(repr(t[idx-100:idx+50]))
