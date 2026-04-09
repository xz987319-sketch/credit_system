t = open('apply/templates/includes/_dynamic_fields.html', encoding='utf-8').read()
idx = t.find("{% if field.field_type == 'select' %}")
print(f'select if at: {idx}')
# Show 200 chars after it
print(repr(t[idx:idx+300]))
