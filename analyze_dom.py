import urllib.request
import re

html = urllib.request.urlopen('http://127.0.0.1:8002/apply/apply/1/?step=1').read().decode('utf-8')

# Find ALL form-groups with proper nesting
fg_pattern = re.compile(r'<div class="form-group"[^>]*>')
fg_starts = [m.start() for m in fg_pattern.finditer(html)]
print(f'Found {len(fg_starts)} form-groups')

# Find invalid-feedback positions
error_positions = [m.start() for m in re.finditer('class="invalid-feedback"', html)]
print(f'Found {len(error_positions)} invalid-feedback elements\n')

for i, fg_start in enumerate(fg_starts[:20]):
    # Find the </div> that closes this form-group
    # Start searching AFTER the > of the opening div
    open_gt = html.find('>', fg_start)
    search_start = open_gt + 1
    
    depth = 1  # we're inside the form-group
    end_pos = search_start
    for m in re.finditer(r'<div|</div>', html[search_start:search_start+10000]):
        if m.group() == '<div':
            depth += 1
        else:
            depth -= 1
            if depth <= 0:
                end_pos = search_start + m.start() + 6
                break
    
    # Get field ids in this form-group
    segment = html[fg_start:end_pos]
    field_ids = re.findall(r'<input[^>]*id="([^"]+)"', segment)
    
    # Check for error div
    has_error = 'invalid-feedback' in segment
    
    if field_ids or has_error or i < 5:
        print(f'FG{i+1} pos={fg_start}-{end_pos}: fields={field_ids}, error={has_error}, size={end_pos-fg_start}')

print('\n--- Which form-group contains each invalid-feedback? ---')
for pos in error_positions:
    nearest_fg = max([fg for fg in fg_starts if fg < pos], default=-1)
    segment = html[nearest_fg:pos+200]
    field_ids = re.findall(r'<input[^>]*id="([^"]+)"', segment)
    print(f'Error at {pos}: nearest_fg={nearest_fg}, fields={field_ids[:3]}')
