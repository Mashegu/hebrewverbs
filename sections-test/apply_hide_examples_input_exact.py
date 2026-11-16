from pathlib import Path

p = Path('/var/www/hebrewverbs-clean/verbs.html')
s = p.read_text(encoding='utf-8')
old = 'body.independent-examples-mode #verbsPanel #verbSearchWrap{display:block!important}'
new = 'body.independent-examples-mode #verbsPanel #verbSearchWrap{display:none!important}'
if s.count(old) != 1:
    raise SystemExit('СТОП: ожидаемое правило не найдено ровно один раз. Файл не изменён.')
# Remove earlier unsuccessful exact insertion, if present.
previous = 'body.independent-examples-mode #verbSearchWrap{display:none!important}\n'
s = s.replace(previous, '')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('OK: в существующем правиле раздела «Примеры» поле скрыто; другие функции не изменены; без резервной копии.')
