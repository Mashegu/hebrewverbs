from pathlib import Path
import re
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
original=s

def block_edit(style_id, fn):
    global s
    pattern=r'(<style\s+id="'+re.escape(style_id)+r'"[^>]*>)(.*?)(</style>)'
    m=re.search(pattern,s,re.S)
    if not m: raise SystemExit('СТОП: не найден существующий блок '+style_id)
    revised=fn(m.group(2))
    s=s[:m.start(2)]+revised+s[m.end(2):]

def change(css, old, new):
    if css.count(old)!=1: raise SystemExit('СТОП: не найдено единственное правило: '+old[:85])
    return css.replace(old,new,1)

def compact(css):
    css=change(css,'.reference-header{min-height:70px!important;padding:5px 7px 5px 8px!important;gap:2px!important;border-radius:10px!important}', '.reference-header{min-height:116px!important;padding:6px 8px!important;gap:2px!important;border-radius:10px!important;flex-wrap:wrap!important;align-content:center!important}')
    css=change(css,'.reference-sections{gap:1px!important;justify-content:center!important}', '.reference-sections{gap:1px!important;justify-content:center!important;flex:1 1 100%!important}')
    css=change(css,'.reference-section{font-size:clamp(13px,3.8vw,20px)!important;line-height:1.08!important;letter-spacing:-.25px!important}', '.reference-section{font-size:24px!important;line-height:1.08!important;letter-spacing:-.25px!important}')
    css=change(css,'.reference-controls{gap:3px!important}', '.reference-controls{gap:3px!important;margin-left:auto!important}')
    css=change(css,'.reference-controls .lang-btn{font-size:clamp(15px,4vw,22px)!important;line-height:1.1!important}', '.reference-controls .lang-btn{font-size:25px!important;line-height:1.1!important}')
    css=change(css,'.reference-controls #sortBtn{width:26px!important;min-width:26px!important;height:29px!important;font-size:24px!important}', '.reference-controls #sortBtn{width:35px!important;min-width:35px!important;height:37px!important;font-size:32px!important}')
    css=change(css,'.reference-controls .back-btn{width:26px!important;min-width:26px!important;height:32px!important}', '.reference-controls .back-btn{width:34px!important;min-width:34px!important;height:39px!important}')
    css=change(css,'.reference-controls .back-mark{width:19px!important;height:19px!important;border-left-width:5px!important;border-bottom-width:5px!important;margin-left:7px!important}', '.reference-controls .back-mark{width:24px!important;height:24px!important;border-left-width:6px!important;border-bottom-width:6px!important;margin-left:7px!important}')
    css=change(css,' .reference-section{font-size:clamp(12px,3.65vw,16px)!important}', ' .reference-section{font-size:24px!important}')
    css=change(css,' .reference-controls .lang-btn{font-size:clamp(14px,3.8vw,18px)!important}', ' .reference-controls .lang-btn{font-size:25px!important}')
    return css
block_edit('compact-header-adjustment-20261009',compact)

def mobile(css):
    css=change(css,'.reference-header .reference-section { font-size:clamp(17px,4.8vw,21px)!important;', '.reference-header .reference-section { font-size:24px!important;')
    css=change(css,'.reference-header .reference-controls .lang-btn { font-size:clamp(19px,5vw,23px)!important; }', '.reference-header .reference-controls .lang-btn { font-size:25px!important; }')
    css=change(css,'.reference-header .reference-controls #sortBtn { font-size:27px!important; }', '.reference-header .reference-controls #sortBtn { font-size:32px!important; }')
    css=change(css,'.reference-header .reference-controls .back-mark { width:21px!important; height:21px!important; }', '.reference-header .reference-controls .back-mark { width:24px!important; height:24px!important; }')
    css=change(css,'  .reference-header .reference-section { font-size:16px!important; }', '  .reference-header .reference-section { font-size:24px!important; }')
    css=change(css,'  .reference-header .reference-controls .lang-btn { font-size:19px!important; }', '  .reference-header .reference-controls .lang-btn { font-size:25px!important; }')
    return css
block_edit('mobile-fonts-only-20261114',mobile)

def examples(css):
    css=change(css,'font:700 16px/1.2 Arial,Helvetica,sans-serif!important;padding:4px 6px!important;white-space:normal!important}', 'font:700 22px/1.2 Arial,Helvetica,sans-serif!important;padding:4px 6px!important;white-space:normal!important}')
    css=change(css,"font:900 34px/1.08 David,'Times New Roman',serif!important;padding:7px 6px 9px!important", "font:900 42px/1.12 David,'Times New Roman',serif!important;padding:7px 6px 9px!important")
    return css
block_edit('examples-unified-appearance-20261011',examples)
# The input and buttons share a container. Its button row has inline top:46px!important.
# Move the buttons visually, leaving all inline JS/HTML and click targets unchanged.
def controls(css):
    old='body.independent-examples-mode #alwaysAiCodeRemove{display:inline-flex!important}'
    new='body.independent-examples-mode #alwaysAiCodeRemove{display:inline-flex!important}\nbody.independent-examples-mode #alwaysAiCodeCell{transform:translateY(-46px)!important}'
    return change(css,old,new)
block_edit('unified-three-controls-fix',controls)
if s==original: raise SystemExit('СТОП: изменений нет')
p.write_text(s,encoding='utf-8')
print('OK: увеличена шапка, кнопки подняты, примеры 42/22 px. Изменены только существующие блоки CSS; без резервной копии.')
