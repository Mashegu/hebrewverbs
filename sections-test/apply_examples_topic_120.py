from pathlib import Path
p = Path('/var/www/hebrewverbs-clean/verbs.html')
s = p.read_text(encoding='utf-8')
old = "var topic='Составь 5 коротких предложений на иврите с глаголом '+(inf.he||query)+'. Время: '+labels[tense]+'. Используй эти формы с огласовками: '+sample+'. Переводы ru, uk, en.';"
new = "var topic=((inf.he||query)+'; '+labels[tense]+'; '+sample+'; 5 предложений с огласовками, переводы ru uk en').slice(0,120);"
if s.count(old) != 1:
    raise SystemExit('STOP: exact Examples AI request not found once; file unchanged')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('OK: Examples AI topic capped at 120 characters; other sections unchanged; no backup')
