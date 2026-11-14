from pathlib import Path
import re

page = Path('/var/www/hebrewverbs-clean/verbs.html')
marker = 'mobile-fonts-only-20261114'
css = '''<style id="mobile-fonts-only-20261114">
/* Mobile-only typography. Does not change JavaScript, data or desktop layout. */
@media screen and (max-width: 600px) {
  .reference-header .reference-section { font-size:clamp(17px,4.8vw,21px)!important; line-height:1.12!important; letter-spacing:-.35px!important; }
  .reference-header .reference-controls .langs { gap:4px!important; padding:1px!important; }
  .reference-header .reference-controls .lang-btn { font-size:clamp(19px,5vw,23px)!important; }
  .reference-header .reference-controls #sortBtn { font-size:27px!important; }
  .reference-header .reference-controls .back-mark { width:21px!important; height:21px!important; }
  #verbSearch { font-size:19px!important; }
  #alwaysAiCodeAI,#alwaysAiCodeAdd,#alwaysAiCodeRemove { font-size:27px!important; }
  .conj-inf-card .tr,.verb .translation,.conj-row-card .form-translation,
  .example-card .example-translation { font-size:18px!important; line-height:1.23!important; }
  .conj-inf-card .he,.verb .hebrew,.conj-row-card .form-hebrew,
  .example-card .example-hebrew { font-size:36px!important; line-height:1.2!important; }
  .conj-person { font-size:.72em!important; }
  .tense-name { font-size:22px!important; }
  #verbsSavedOverlay .db-tr { font-size:19px!important; }
  #verbsSavedOverlay .db-he { font-size:35px!important; line-height:1.2!important; }
  .conj-table .form-hebrew { font-size:29px!important; }
  .conj-table .form-translation,.conj-table .tr-cell { font-size:16px!important; }
  .conj-table .person-cell { font-size:18px!important; }
  #hebrewRootsWorkspace .db-tr { font-size:19px!important; }
  #hebrewRootsWorkspace .db-he,#hebrewRootsWorkspace .roots-he { font-size:35px!important; }
}
@media screen and (max-width: 370px) {
  .reference-header .reference-section { font-size:16px!important; }
  .reference-header .reference-controls .lang-btn { font-size:19px!important; }
}
</style>'''
text = page.read_text(encoding='utf-8')
if marker in text:
    text, n = re.subn(r'<style id="'+marker+r'">.*?</style>', css, text, flags=re.S)
    if n != 1:
        raise SystemExit('ERROR: mobile style marker occurs unexpectedly')
else:
    if '</body>' not in text:
        raise SystemExit('ERROR: HTML body closing tag not found; nothing changed')
    text = text.replace('</body>', css + '\n</body>', 1)
page.write_text(text, encoding='utf-8')
print('OK: mobile font sizes updated; desktop, JavaScript, verbsDB unchanged')
