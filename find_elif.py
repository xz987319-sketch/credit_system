template = open('apply/templates/h5_multi_step_form.html', encoding='utf-8').read()
# Search for elif field.field_type == 'text' and field.validation_rule == 'name'
search = "field.field_type == 'text' and field.validation_rule == 'name'"
idx = template.find(search)
print(f'Found at position: {idx}')

# Show before and after
print('\nBEFORE (300 chars):')
print(repr(template[idx-300:idx]))
print('\nMATCH:')
print(repr(template[idx:idx+len(search)+50]))
print('\nAFTER (200 chars):')
print(repr(template[idx+len(search)+50:idx+len(search)+150]))

# Also find the outer if line
outer = "field.field_type == 'name' or field.validation_rule == 'name'"
outer_idx = template.find(outer)
print(f'\nOuter if position: {outer_idx}')
print('Around outer if:')
print(repr(template[outer_idx-50:outer_idx+len(outer)+50]))
