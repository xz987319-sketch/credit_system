import urllib.request
import re

url = 'http://127.0.0.1:8000/apply/apply/1/?step=1'
try:
    resp = urllib.request.urlopen(url, timeout=5)
    html = resp.read().decode('utf-8')

    # Check which template is rendered
    if 'h5_multi_step_form' in html[:2000]:
        print('USING h5_multi_step_form.html')
    else:
        print('UNKNOWN template')

    # Find all inputs with OT1_ or KI_ in id
    pattern = r'<input[^>]*id="(OT1_|KI_)[^"]*"[^>]*>'
    matches = re.findall(pattern, html)
    print(f'Found {len(matches)} OT1_/KI_ fields')

    # Find specific fields
    for field_id in ['OT1_NAME', 'OT1_FA_MOBILE', 'KI_NAME', 'KI_FA_MOBILE']:
        idx = html.find('id="' + field_id + '"')
        if idx >= 0:
            print(f'\n=== {field_id} ===')
            
            # Find the parent form-group div start
            form_group_start = html.rfind('<div class="form-group">', 0, idx)
            if form_group_start < 0:
                form_group_start = html.rfind('<div class="form-group ', 0, idx)
            
            # Find the closing </div> - count opens and closes
            search_start = idx
            depth = 0
            form_group_end = -1
            for m in re.finditer(r'<div|</div>', html[search_start:search_start+20000]):
                if m.group() == '<div':
                    depth += 1
                else:
                    depth -= 1
                    if depth <= 0:
                        form_group_end = search_start + m.start()
                        break
            
            if form_group_start >= 0 and form_group_end > form_group_start:
                form_group_html = html[form_group_start:form_group_end+6]
                error_idx = form_group_html.find('invalid-feedback')
                if error_idx >= 0:
                    print('FOUND invalid-feedback at offset', error_idx, 'in form-group')
                    print('CONTEXT:', form_group_html[max(0,error_idx-80):error_idx+120])
                else:
                    print('NO invalid-feedback div in form-group!')
                    print('Form-group snippet (500-1500):')
                    print(form_group_html[500:1500])
            else:
                print(f'Could not find form-group: start={form_group_start}, end={form_group_end}')
        else:
            print(f'\n=== {field_id} === NOT FOUND')

except Exception as e:
    print(f'Error: {e}')
