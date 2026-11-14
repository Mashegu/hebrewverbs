from pathlib import Path
import re
p=Path('/var/www/hebrewverbs-clean/verbs.html')
s=p.read_text(encoding='utf-8')
marker='/* examples-ai-progress-indicator-20261114 */'
start=s.find(marker)
if start<0: raise SystemExit('ERROR: existing examples indicator marker not found; no changes')
end=s.find('</script>',start)
if end<0: raise SystemExit('ERROR: script boundary not found; no changes')
chunk=s[start:end]
pattern=r'function examplesAiProgress\(text\)\s*\{.*?\n\}'
m=re.search(pattern,chunk,re.S)
if not m:
    # Previous implementation uses compact one-line closing brace; anchor on next script boundary.
    pattern=r'function examplesAiProgress\(text\)\s*\{[\s\S]*?(?=\n\s*</script>)'
    m=re.search(pattern,chunk)
if not m: raise SystemExit('ERROR: indicator function not found; no changes')
new='''function examplesAiProgress(text){
  var id='examples-ai-progress-fixed';
  var node=document.getElementById(id);
  if(!text){if(node)node.remove();return;}
  if(!document.body.classList.contains('independent-examples-mode'))return;
  var anchor=document.getElementById('alwaysAiCodeCell');
  if(!anchor){return;}
  if(!node){node=document.createElement('div');node.id=id;node.setAttribute('role','status');node.setAttribute('aria-live','polite');}
  anchor.insertAdjacentElement('afterend',node);
  node.style.cssText='display:block!important;position:relative!important;visibility:visible!important;opacity:1!important;width:100%!important;max-width:390px!important;box-sizing:border-box!important;margin:8px auto!important;padding:10px 12px!important;background:#fff2bd!important;border:2px solid #c79800!important;border-radius:8px!important;color:#111!important;font:700 16px/1.4 Arial,sans-serif!important;text-align:center!important;z-index:100!important;';
  node.textContent=text;
}'''
newchunk=chunk[:m.start()]+new+chunk[m.end():]
s2=s[:start]+newchunk+s[end:]
if s2==s: raise SystemExit('ERROR: no changes')
p.write_text(s2,encoding='utf-8')
print('OK: Examples AI indicator placed below AI/+/- buttons; other sections unchanged; no backup')
