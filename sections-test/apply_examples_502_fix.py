from pathlib import Path

path = Path('/opt/hebrewverbs-ai/hebrewverbs_ai_api_protected.py')
source = path.read_text(encoding='utf-8')
old = "if expected is not None and (len(items) not in (9, 10) if section in ('reading', 'examples') else len(items) != expected):"
new = "if expected is not None and (not (1 <= len(items) <= 10) if section == 'examples' else (len(items) not in (9, 10) if section == 'reading' else len(items) != expected)):"
if source.count(old) != 1:
    raise SystemExit('STOP: expected validation line not found exactly once; no changes made')
updated = source.replace(old, new, 1)
compile(updated, str(path), 'exec')
path.write_text(updated, encoding='utf-8')
print('OK: examples accepts 1-10 sentences; reading and verbs unchanged; no backup')
