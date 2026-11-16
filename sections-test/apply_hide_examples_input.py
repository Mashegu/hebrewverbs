from pathlib import Path
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
marker='id="examples-hide-input-only-20261116"'
css='''<style id="examples-hide-input-only-20261116">
/* Hide only the shared verb input in Examples; keep it in DOM for saved-list selection. */
body.independent-examples-mode #verbSearchWrap { display:none!important; }
</style>
'''
if marker in s:
    print('OK: поле ввода в разделе «Примеры» уже скрыто; изменений нет')
elif s.count('</head>') != 1 or 'independent-examples-mode' not in s or 'id="verbSearchWrap"' not in s:
    print('STOP: структура файла не совпадает; изменений нет')
else:
    p.write_text(s.replace('</head>',css+'</head>',1),encoding='utf-8')
    print('OK: скрыто только поле ввода в разделе «Примеры»; остальные разделы и функции не изменены; без резервной копии')
